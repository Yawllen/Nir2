"""Пересчет метрик и рисунков НИР по сохраненным результатам классификатора."""

import csv
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT.parent / "printer-defect-server" / "models" / "spaghetti_presence_v12"
CORRECTED = "9450355e6df422128eb97ea9b6020020b02ff3f0e2c2f65267ddd84115c1352c"
THRESHOLDS = (0.1, 0.25, 0.3, 0.5)


def average_precision(rows):
    ordered = sorted(rows, key=lambda row: row["score"], reverse=True)
    positive = sum(row["label"] for row in rows)
    if not positive:
        return None
    found = previous = 0
    result = 0.0
    for index, row in enumerate(ordered):
        found += row["label"]
        if index == len(ordered) - 1 or ordered[index + 1]["score"] != row["score"]:
            result += (found - previous) / positive * found / (index + 1)
            previous = found
    return result


def metrics(rows, threshold):
    tp = sum(row["label"] == 1 and row["score"] >= threshold for row in rows)
    fp = sum(row["label"] == 0 and row["score"] >= threshold for row in rows)
    fn = sum(row["label"] == 1 and row["score"] < threshold for row in rows)
    tn = sum(row["label"] == 0 and row["score"] < threshold for row in rows)
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
        "accuracy": (tp + tn) / len(rows),
        "false_alarm_rate": fp / (fp + tn) if fp + tn else None,
    }


assert abs(average_precision([
    {"label": 1, "score": 0.8}, {"label": 0, "score": 0.7},
    {"label": 1, "score": 0.6},
]) - 5 / 6) < 1e-12
assert average_precision([{"label": 1, "score": 0.5}, {"label": 0, "score": 0.5}]) == 0.5
assert metrics([{"label": 1, "score": 0.3}, {"label": 0, "score": 0.2}], 0.3)["tp"] == 1
assert metrics([{"label": 1, "score": 0.3}, {"label": 0, "score": 0.2}], 0.4)["fn"] == 1

predictions = json.loads((SOURCE / "classification_predictions.json").read_text(encoding="utf-8"))
archive = json.loads((SOURCE / "classification_metrics.json").read_text(encoding="utf-8"))
history = json.loads((SOURCE / "history.json").read_text(encoding="utf-8"))
metadata = json.loads((SOURCE / "run_metadata.json").read_text(encoding="utf-8"))
assert len(history) == 20 and metadata["best_epoch"] == 19
eligible = [row for row in history if row["target_at_0_3"]["false_alarm_rate"] <= 0.01]
selected = max(eligible, key=lambda row: (
    row["target_at_0_3"]["recall"], -row["target_at_0_3"]["false_alarm_rate"],
    row["target_at_0_3"]["image_AP"], row["image_AP"],
))
assert selected["epoch"] == metadata["best_epoch"]
for split, rows in predictions.items():
    assert abs(average_precision(rows) - archive[split]["image_AP"]) < 1e-12
    assert all(row["label"] in (0, 1) and 0 <= row["score"] <= 1 for row in rows)
    for threshold in THRESHOLDS:
        computed = metrics(rows, threshold)
        stored = archive[split]["thresholds"][str(threshold)]
        for key in computed:
            assert computed[key] == stored[key] or abs(computed[key] - stored[key]) < 1e-12
corrected = [row for row in predictions["test"] if row["sha256"] == CORRECTED]
assert len(corrected) == 1 and corrected[0]["label"] == 1
corrected[0]["label"] = 0
with (SOURCE / "dataset_manifest.csv").open(encoding="utf-8-sig", newline="") as stream:
    manifest = {row["sha256"]: row for row in csv.DictReader(stream)}
for split, rows in predictions.items():
    for row in rows:
        expected = 0 if split == "test" and row["sha256"] == CORRECTED else int(manifest[row["sha256"]]["label"])
        assert manifest[row["sha256"]]["split"] == split and row["label"] == expected
result = {
    "model": metadata["model_version"], "checkpoint_sha256": metadata["checkpoint_sha256"],
    "best_epoch": metadata["best_epoch"], "corrected_test_frame": CORRECTED,
    "sources_sha256": {name: hashlib.sha256((SOURCE / name).read_bytes()).hexdigest()
                       for name in ("classification_predictions.json", "history.json", "run_metadata.json", "dataset_manifest.csv")},
    "splits": {},
}
for split, rows in predictions.items():
    printer = [row for row in rows if row["origin"].startswith("printer_")]
    result["splits"][split] = {
        "images": len(rows), "image_AP": average_precision(rows),
        "thresholds": {str(t): metrics(rows, t) for t in THRESHOLDS},
        "printer_at_0_3": metrics(printer, 0.3),
    }
assert [result["splits"][s]["images"] for s in ("valid", "test")] == [3005, 3337]
assert [result["splits"]["test"]["thresholds"]["0.3"][key] for key in ("tp", "fp", "fn", "tn")] == [916, 12, 1, 2408]

plt.rcParams.update({"font.family": "Times New Roman", "font.size": 20,
                     "axes.titlesize": 22, "axes.labelsize": 20,
                     "xtick.labelsize": 18, "ytick.labelsize": 18,
                     "legend.fontsize": 17, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.formatter.use_locale": False})
blue, orange, green = "#17648b", "#b44c18", "#27704c"


def save(figure, name):
    destination = ROOT / "fig" / ("spaghetti-v5-" + name + ".png")
    temporary = destination.with_name(destination.stem + ".tmp.png")
    figure.savefig(temporary, dpi=300, facecolor="white", bbox_inches="tight")
    temporary.replace(destination)
    plt.close(figure)


epochs = [row["epoch"] for row in history]
fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.2), layout="constrained")
axes[0].plot(epochs, [row["loss"] for row in history], color=blue, marker="o", linewidth=2)
axes[0].set_yscale("log")
axes[0].set_title("Ошибка обучения")
axes[0].set_ylabel("Бинарная перекрестная\nэнтропия, безразмерная")
axes[1].plot(epochs, [100 * row["image_AP"] for row in history], color=blue, marker="o", linewidth=2)
axes[1].set_title("Вся валидация")
axes[1].set_ylabel("AP, %")
axes[1].set_ylim(98.5, 100)
axes[2].plot(epochs, [100 * row["target_at_0_3"]["recall"] for row in history], color=blue, marker="o", linewidth=2, label="Полнота")
axes[2].plot(epochs, [100 * row["target_at_0_3"]["false_alarm_rate"] for row in history], color=orange, marker="s", linewidth=2, label="Ложные тревоги")
axes[2].axhline(1, color="#444444", linestyle=":", linewidth=1.5, label="Лимит 1 %")
axes[2].set_title("Валидация принтера\nПорог 0,3")
axes[2].set_ylabel("Доля кадров, %")
axes[2].set_ylim(-3, 100)
axes[2].legend(loc="upper left")
for axis in axes:
    axis.axvline(19, color="#444444", linestyle="--", linewidth=1.5)
    axis.set_xlabel("Эпоха")
    axis.set_xticks([1, 5, 10, 15, 20])
    axis.tick_params(axis="x", labelsize=16)
    axis.grid(axis="y", alpha=0.18)
save(fig, "training")

fig, axes = plt.subplots(2, 2, figsize=(8.7, 7.8), layout="constrained")
for row_index, threshold in enumerate((0.3, 0.5)):
    for column_index, split in enumerate(("valid", "test")):
        axis = axes[row_index, column_index]
        values = result["splits"][split]["thresholds"][str(threshold)]
        matrix = np.array([[values["tn"], values["fp"]], [values["fn"], values["tp"]]])
        axis.imshow(matrix, cmap="Blues", vmin=0, vmax=2420)
        for y in range(2):
            for x in range(2):
                axis.text(x, y, str(matrix[y, x]), ha="center", va="center",
                          color="white" if matrix[y, x] > 1300 else "black", fontsize=25)
        axis.set_xticks([0, 1], ["Нет", "Есть"])
        axis.set_yticks([0, 1], ["Нет", "Есть"])
        axis.set_xlabel("Ответ модели")
        axis.set_ylabel("Эталонная метка")
        axis.set_title(("Валидация" if split == "valid" else "Тест") + "\nПорог " + str(threshold).replace(".", ","))
save(fig, "confusion")

fig, axes = plt.subplots(2, 2, figsize=(12.6, 6.7), layout="constrained")
for row_index, split in enumerate(("valid", "test")):
    values = result["splits"][split]["thresholds"]
    label = "Валидация" if split == "valid" else "Тест"
    for key, caption, color, marker in (("precision", "Точность", blue, "o"),
                                       ("recall", "Полнота", orange, "s"),
                                       ("f1", "F1", green, "^")):
        axes[row_index, 0].plot(THRESHOLDS, [100 * values[str(t)][key] for t in THRESHOLDS],
                                color=color, marker=marker, linewidth=2, label=caption)
    axes[row_index, 0].set_title(label + ":\nточность, полнота и F1")
    axes[row_index, 0].set_ylabel("Показатель, %")
    axes[row_index, 0].set_ylim(98, 100)
    axes[row_index, 0].legend(loc="lower right", ncol=3, fontsize=15)
    axes[row_index, 1].plot(THRESHOLDS, [100 * values[str(t)]["false_alarm_rate"] for t in THRESHOLDS],
                           color=orange, marker="s", linewidth=2)
    axes[row_index, 1].set_title(label + ":\nложные тревоги")
    axes[row_index, 1].set_ylabel("От отрицательных кадров, %")
    axes[row_index, 1].set_ylim(0, 0.75)
    for axis in axes[row_index]:
        axis.axvline(0.3, color="#444444", linestyle="--", linewidth=1.5)
        axis.set_xlabel("Порог")
        axis.set_xticks(THRESHOLDS, [str(t).replace(".", ",") for t in THRESHOLDS])
        axis.grid(axis="y", alpha=0.18)
save(fig, "thresholds")
(Path(__file__).parent / "metrics_v12.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("Метрики и три рисунка обновлены. Проверены архивная оценка, уточненная метка, состав выборок и выбор эпохи 19.")
