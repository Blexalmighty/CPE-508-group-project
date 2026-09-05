# Drop trained models here

The model files are not in git — `random_forest_model.pkl` is 121 MB, over
GitHub's 100 MB per-file limit. They live in a private release instead:

```bash
gh release download models-v1 --repo Blexalmighty/CPE-508-group-project --dir backend/models
```

The backend loads one file at startup, trying these names in order:

| File | Notes |
| --- | --- |
| `random_forest_model.pkl` | Report §4.4 deployment engine — **currently serving** |
| `model.pkl` | The XGBoost bundle |
| `xgb_Tumor_Response_model.json` | Same XGBoost model, saved natively |

The two engines do not take the same features. Random Forest was trained on 14
columns, excluding `Overall_Survival_Months` as leakage; the XGBoost bundle uses
all 15. The API reads the column list from whichever file it loads, so both work
without a code change — but a prediction from one is not comparable to the other.

If none of those names exist but the folder holds exactly one supported file,
that file is used. Accepted extensions: `.pkl`, `.joblib`, `.json`, `.ubj`.

Because `random_forest_model.*` is checked first, dropping it in and restarting
uvicorn is all that's needed to switch engines — no code change.

## Expected file format

Two shapes load. Whichever you save, the file has to declare the columns it was
trained on — the API builds its feature frame to match that list, which is why a
different column order, or a different number of columns, still works.

A bundle, which is what the XGBoost notebook produced:

```python
joblib.dump({
    "model": clf,                     # anything with predict_proba
    "feature_columns": feature_cols,  # exact training column order
    "target": "Tumor_Response",
}, "model.pkl")
```

Or a bare estimator or `Pipeline`, which is what `random_forest_train.py`
produced:

```python
joblib.dump(rf_best, "random_forest_model.pkl")
```

That works because scikit-learn records `feature_names_in_` when the model is
fitted on a DataFrame. Fit on a raw NumPy array instead and the attribute is
absent — the loader then rejects the file rather than guessing a column order.
The bundle form is still preferable: it also carries the target name, where a bare
estimator makes the API assume `Tumor_Response`.

## The preprocessing contract

`../features.py` reproduces report §3.1.2 exactly — the 0/1 maps, the ordinal
maps, the four `LabelEncoder` lookups, and min-max scaling over the documented
ranges. The API applies that to raw form values before calling the model.

This is verified rather than assumed: `model.pkl` and
`xgb_Tumor_Response_model.json` are the same trained model saved two ways, and
feeding both through `features.build_frame` produces identical probabilities to
15 decimal places. If they had disagreed, the encoding would be wrong.

So if you retrain with different encodings, `../features.py` has to change too.
A mismatch there does not raise — it produces confident wrong numbers.

## Checking it loaded

```bash
curl http://127.0.0.1:8000/api/health
```

`detail` reports the filename, estimator class, target, and feature count, e.g.
`model.pkl: XGBClassifier predicting Tumor_Response over 15 features`.

`/api/health` needs no token. `/api/predict` does — see the Authentication
section of the root README.

## Notes

- Pickles are version-sensitive. If loading fails with an attribute or module
  error, the training environment's scikit-learn/XGBoost versions differ from
  `../requirements.txt` — match them and reinstall.
- Model files are gitignored; they are shared out of band, not committed.
- `confusion_matrix.png` and `xgboost_results.xlsx` sit here as training
  artefacts. The loader ignores them — it only looks at the four model
  extensions.
