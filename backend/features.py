"""Maps the form payload onto the feature frame the models were trained on.

Everything here mirrors section 3.1.2 of the project report: the same 0/1 and
ordinal maps, the same LabelEncoder lookups, and the same min-max ranges. That
matters more than it looks -- a wrong code here does not raise, it just shifts a
feature and produces a confident wrong answer. This is the first file to check
when predictions look off.

Between them the models use these 16 columns:

    Sex  Tumor_Stage  Metastasis_Status  Neutropenia  Overall_Survival_Months
    Smoking_Status_Code  Cancer_Type_Code  Genetic_Mutation_Code
    Chemotherapy_Regimen_Code  Age_scaled  BMI_scaled  Tumor_Size_scaled
    Dosage (mg/m2)_scaled  Cycles_Completed_scaled  Nausea_Severity_scaled

No single model wants all of them. build_frame emits exactly the columns the
loaded model declares, so this module can encode a superset:

    XGBoost (model.pkl)                15 of them
    Random Forest (the report 4.4 pick) 14 -- it drops Overall_Survival_Months,
                                       excluded during training as leakage,
                                       being a downstream outcome

That is why _encode returns a dict keyed by slug rather than a fixed-order row.
"""

import re

import pandas as pd

# Report 3.1.2 step 4 -- binary and ordinal maps.
SEX = {"Male": 0, "Female": 1}
YES_NO = {"No": 0, "Yes": 1}
TUMOR_STAGE = {"I": 1, "II": 2, "III": 3, "IV": 4}

# Report 3.1.2 step 4 -- LabelEncoder lookups, alphabetical as sklearn produces.
SMOKING_STATUS = {"Current": 0, "Former": 1, "Never": 2}
CANCER_TYPE = {"Breast": 0, "Colon": 1, "Leukemia": 2, "Lung": 3, "Lymphoma": 4}
GENETIC_MUTATION = {"BRCA1": 0, "EGFR": 1, "KRAS": 2, "None": 3, "TP53": 4}
CHEMO_REGIMEN = {"ABVD": 0, "CHOP": 1, "FOLFOX": 2, "Gemcitabine": 3, "None": 4}

# Tumor_Response was mapped in clinical order, worst to best -- not alphabetical.
RESPONSE_CLASSES = ("Progressive", "Stable", "Partial", "Complete")

# "Responded" for the dashboard means Partial or Complete.
FAVOURABLE_CLASSES = (2, 3)

# Report 3.1.2 step 3 -- documented valid ranges, which step 3 confirms every row
# already sat inside. MinMaxScaler was fit on those rows, so over 52,321 patients
# its learned min/max are these bounds.
SCALE_RANGES = {
    "age": (30.0, 85.0),
    "bmi": (18.5, 35.0),
    "tumorsize": (1.0, 10.0),
    "dosagemgm": (50.0, 600.0),
    "cyclescompleted": (1.0, 8.0),
    "nauseaseverity": (1.0, 5.0),
}

# Overall_Survival_Months is a feature but was never scaled, so it goes in raw.


def slug(column: str) -> str:
    """Training column name -> the key used in this module.

    Matching on alphanumerics only, with the _scaled/_Code suffix stripped, keeps
    the superscript two in "Dosage (mg/m2)_scaled" out of this file -- that one
    character does not survive every editor and console it passes through.
    """
    base = re.sub(r"_(scaled|Code)$", "", column)
    return re.sub(r"[^a-z0-9]", "", base.lower())


def build_frame(patient, columns) -> pd.DataFrame:
    """Single-row frame for `columns`, in the order the model declared them."""
    values = _encode(patient)

    # Extra keys in `values` are fine and expected -- a model that ignores a
    # column simply never asks for it. Only the reverse is a problem.
    missing = [c for c in columns if slug(c) not in values]
    if missing:
        raise ValueError(
            f"No form field maps to {missing}. The model was trained on columns "
            "this form does not collect -- add them to src/lib/fields.js and to "
            "_encode() below."
        )

    return pd.DataFrame([[values[slug(c)] for c in columns]], columns=list(columns))


def _encode(patient) -> dict[str, float]:
    scaled = {
        "age": patient.age,
        "bmi": patient.bmi,
        "tumorsize": patient.tumorSizeCm,
        "dosagemgm": patient.dosage,
        "cyclescompleted": patient.cyclesCompleted,
        "nauseaseverity": patient.nauseaSeverity,
    }
    row = {name: _min_max(name, value) for name, value in scaled.items()}

    row["sex"] = _code("sex", SEX, patient.sex)
    row["tumorstage"] = _code("tumorStage", TUMOR_STAGE, patient.tumorStage)
    row["metastasisstatus"] = _code("metastasisStatus", YES_NO, patient.metastasisStatus)
    row["neutropenia"] = _code("neutropenia", YES_NO, patient.neutropenia)
    row["smokingstatus"] = _code("smokingStatus", SMOKING_STATUS, patient.smokingStatus)
    row["cancertype"] = _code("cancerType", CANCER_TYPE, patient.cancerType)
    row["geneticmutation"] = _code("geneticMutation", GENETIC_MUTATION, patient.geneticMutation)
    row["chemotherapyregimen"] = _code("chemoRegimen", CHEMO_REGIMEN, patient.chemoRegimen)
    row["overallsurvivalmonths"] = float(patient.survivalMonths)

    return row


def _code(field: str, mapping: dict[str, int], value: str) -> int:
    if value not in mapping:
        raise ValueError(
            f"{field}={value!r} is not a category the model was trained on. "
            f"Expected one of {sorted(mapping)}."
        )
    return mapping[value]


def _min_max(name: str, value) -> float:
    """Reproduce MinMaxScaler for one column.

    Clamped because the training data contained no out-of-range values, so the
    models never saw a scaled feature outside [0, 1]. The request schema rejects
    out-of-range numbers first; this is the second line of defence.
    """
    low, high = SCALE_RANGES[name]
    return min(1.0, max(0.0, (float(value) - low) / (high - low)))
