"""
STEP 1: Random Forest model for predicting Tumor_Response.

Target: Tumor_Response (4 classes: 0, 1, 2, 3)
Excluded from features: Patient_ID (not predictive),
                        Overall_Survival_Months (leakage risk - it's
                        a downstream outcome, not a predictor)

Run: python random_forest_train.py
"""

import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, ConfusionMatrixDisplay
)
import matplotlib.pyplot as plt
import joblib

# ------------------------------------------------------------------
# 1. CONFIG
# ------------------------------------------------------------------
DATA_PATH = "chemotherapy_patient_data_clean.csv"
TARGET_COL = "Tumor_Response"
RANDOM_STATE = 42
TEST_SIZE = 0.2
AVERAGE_METHOD = "weighted"  # multi-class (4 classes)

NOMINAL_COLS = [
    "Cancer_Type_Code",
    "Genetic_Mutation_Code",
    "Chemotherapy_Regimen_Code",
    "Smoking_Status_Code",
]

NUMERIC_COLS = [
    "Age_scaled",
    "BMI_scaled",
    "Tumor_Size_scaled",
    "Dosage (mg/m²)_scaled",
    "Cycles_Completed_scaled",
    "Nausea_Severity_scaled",
    "Sex",
    "Tumor_Stage",
    "Metastasis_Status",
    "Neutropenia",
]

# ------------------------------------------------------------------
# 2. LOAD DATA
# ------------------------------------------------------------------
df = pd.read_csv(DATA_PATH)
print("Data shape:", df.shape)
print("\nTumor_Response class balance:")
print(df[TARGET_COL].value_counts().sort_index())

X = df[NOMINAL_COLS + NUMERIC_COLS]
y = df[TARGET_COL]
class_names = [str(c) for c in sorted(y.unique())]

# ------------------------------------------------------------------
# 3. TRAIN/TEST SPLIT
# ------------------------------------------------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
)
print(f"\nTrain size: {len(X_train)}, Test size: {len(X_test)}")

# ------------------------------------------------------------------
# 4. PREPROCESSING
# ------------------------------------------------------------------
preprocessor = ColumnTransformer(
    transformers=[("nominal", OneHotEncoder(handle_unknown="ignore"), NOMINAL_COLS)],
    remainder="passthrough",
)

# ------------------------------------------------------------------
# 5. RANDOM FOREST + HYPERPARAMETER SEARCH
# ------------------------------------------------------------------
print("\n" + "=" * 60)
print("Training Random Forest...")
print("=" * 60)

rf_pipeline = Pipeline([
    ("preprocess", preprocessor),
    # n_jobs=1 here on purpose: GridSearchCV already parallelizes across
    # fold/param combinations below, so we don't want RF *also* spawning
    # its own threads inside each of those (that's called "nested
    # parallelism" and it usually slows things down instead of speeding
    # them up, since your cores end up fighting each other).
    ("model", RandomForestClassifier(random_state=RANDOM_STATE, class_weight="balanced", n_jobs=1)),
])

# Fuller grid - 3 x 3 x 3 = 27 parameter combinations.
# With cv=5, that's 135 model fits total.
# On a multi-core machine this should take a few minutes; if it feels
# too slow, trim a value from one of the lists below (e.g. drop 300
# from n_estimators, or drop 4 from min_samples_leaf).
rf_param_grid = {
    "model__n_estimators": [100, 200, 300],
    "model__max_depth": [None, 15, 25],
    "model__min_samples_leaf": [1, 2, 4],
}

# n_jobs=-1 uses all available CPU cores to run different
# fold/param combinations in parallel - this is where the real
# speedup comes from on your machine.
rf_grid = GridSearchCV(rf_pipeline, rf_param_grid, cv=5, scoring="f1_weighted", n_jobs=-1, verbose=2)
rf_grid.fit(X_train, y_train)
rf_best = rf_grid.best_estimator_
print("\nBest RF params:", rf_grid.best_params_)

# ------------------------------------------------------------------
# 6. EVALUATION
# ------------------------------------------------------------------
y_pred = rf_best.predict(X_test)

acc = accuracy_score(y_test, y_pred)
prec = precision_score(y_test, y_pred, average=AVERAGE_METHOD)
rec = recall_score(y_test, y_pred, average=AVERAGE_METHOD)
f1 = f1_score(y_test, y_pred, average=AVERAGE_METHOD)

print("\n=== Random Forest Results ===")
print(f"Accuracy:  {acc:.4f}")
print(f"Precision: {prec:.4f}")
print(f"Recall:    {rec:.4f}")
print(f"F1-score:  {f1:.4f}")
print("\nFull classification report:")
print(classification_report(y_test, y_pred, target_names=class_names))

cm = confusion_matrix(y_test, y_pred)
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=class_names)
disp.plot(cmap="Blues")
plt.title("Confusion Matrix — Random Forest")
plt.tight_layout()
plt.savefig("confusion_matrix_random_forest.png")
plt.close()

# ------------------------------------------------------------------
# 7. SAVE MODEL + RESULTS
# ------------------------------------------------------------------
joblib.dump(rf_best, "random_forest_model.pkl")

results_df = pd.DataFrame([{
    "model": "Random Forest",
    "best_params": rf_grid.best_params_,
    "accuracy": acc,
    "precision": prec,
    "recall": rec,
    "f1": f1,
}])
results_df.to_csv("random_forest_results.csv", index=False)

print("\nSaved: random_forest_model.pkl")
print("Saved: random_forest_results.csv")
print("Saved: confusion_matrix_random_forest.png")
