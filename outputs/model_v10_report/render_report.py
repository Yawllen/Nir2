"""Построить отчёт из сохранённых метрик и предсказаний, без загрузки модели."""

import csv
import hashlib
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.patches import Rectangle
from matplotlib.text import Text
from matplotlib.ticker import FuncFormatter
from PIL import Image


OUT = Path(__file__).resolve().parent
MODELS = OUT.parents[1].parent / "printer-defect-server" / "models"
V10 = MODELS / "spaghetti_presence_v10"
THRESHOLD = 0.3
SOURCES = {
    "our_detail_combined": "Кадры без спагетти",
    "our_spaghetti": "Кадры со спагетти\nиз внешних источников",
    "printer_benchy_spaghetti_20261006": "Печать контрольного изделия",
    "printer_capture_20261003": "Историческая съёмка принтера",
    "stereovision_spaghetti": "Открытый размеченный набор",
}
COUNTS = ("tp", "fp", "fn", "tn")
RATE_KEYS = ("precision", "recall", "f1", "accuracy", "image_AP", "false_alarm_rate")
INPUT_HASHES = {}
FIGURES = []


def read(path):
    content = path.read_bytes()
    INPUT_HASHES[str(path)] = hashlib.sha256(content).hexdigest()
    return json.loads(content.decode("utf-8"))


def fmt(value, digits=2):
    return "—" if value is None else f"{value:.{digits}f}".replace(".", ",")


def integer(value):
    return f"{value:,}".replace(",", " ")


def calculate(records, threshold=THRESHOLD):
    assert records, "Пустая выборка"
    for row in records:
        assert row["label"] in (0, 1)
        assert math.isfinite(row["score"]) and 0 <= row["score"] <= 1
    labels = np.array([r["label"] for r in records], dtype=bool)
    scores = np.array([r["score"] for r in records])
    predicted = scores >= threshold
    tp, fp = int(np.sum(predicted & labels)), int(np.sum(predicted & ~labels))
    fn, tn = int(np.sum(~predicted & labels)), int(np.sum(~predicted & ~labels))
    result = dict(tp=tp, fp=fp, fn=fn, tn=tn,
                  precision=tp / (tp + fp) if tp + fp else None,
                  recall=tp / (tp + fn) if tp + fn else None,
                  f1=2 * tp / max(2 * tp + fp + fn, 1),
                  accuracy=(tp + tn) / len(records),
                  false_alarm_rate=fp / (fp + tn) if fp + tn else None)
    # AP: ступенчатое интегрирование по группам одинаковых score, как в обучении.
    order = np.argsort(-scores, kind="stable")
    sorted_labels, sorted_scores = labels[order], scores[order]
    ends = np.r_[np.flatnonzero(np.diff(sorted_scores)), len(records) - 1]
    positives = np.cumsum(sorted_labels)[ends]
    result["image_AP"] = (float(np.sum(np.diff(np.r_[0, positives]) * positives / (ends + 1))
                                / labels.sum()) if labels.sum() else None)
    return result


def verify(records, published):
    actual = calculate(records)
    for key in COUNTS + RATE_KEYS:
        if key not in published:
            continue
        expected = published[key]
        if expected is None:
            assert actual[key] is None, (key, actual[key], expected)
        else:
            assert actual[key] is not None and math.isclose(actual[key], expected, abs_tol=1e-12), (
                key, actual[key], expected)
    assert sum(actual[key] for key in COUNTS) == len(records)
    return actual


def save(fig, name):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for text in fig.findobj(Text):
        if not text.get_visible() or not text.get_text():
            continue
        assert text.get_fontsize() >= 14, (name, text.get_text(), text.get_fontsize())
        font = font_manager.findfont(text.get_fontproperties(), fallback_to_default=False)
        assert font_manager.FontProperties(fname=font).get_name() == "Times New Roman", font
        box = text.get_window_extent(renderer)
        assert (box.x0 >= -1 and box.y0 >= -1 and box.x1 <= fig.bbox.width + 1
                and box.y1 <= fig.bbox.height + 1), (name, text.get_text(), box)
    fig.savefig(OUT / f"{name}.png", dpi=300, facecolor="white")
    fig.savefig(OUT / f"{name}.pdf", facecolor="white")
    with Image.open(OUT / f"{name}.png") as png:
        assert all(abs(dpi - 300) < 1 for dpi in png.info["dpi"])
        dimensions = list(png.size)
    pdf = (OUT / f"{name}.pdf").read_bytes()
    assert b"/FontFile2" in pdf and b"TimesNewRoman" in pdf
    assert b"/Subtype /Image" not in pdf, "PDF должен быть векторным"
    FIGURES.append(dict(name=name, pixels=dimensions, dpi=300, font="Times New Roman", minimum_font_pt=14,
                        pdf_vector=True, labels_within_canvas=True))
    plt.close(fig)


def plot_history(histories, continuation, parent_epoch, source_epoch):
    fig, axes = plt.subplots(2, 1, figsize=(12.0, 10.4))
    fig.subplots_adjust(left=0.12, right=0.98, bottom=0.27, top=0.8, hspace=0.55)
    styles = [("Версия 5", "#376c9a", "o", "-"),
              ("Версия 8 (r4)", "#627a36", "s", "--"),
              ("Версия 9", "#b47700", "^", "-."),
              ("Версия 10", "#984f79", "D", ":")]
    for rows, (label, color, marker, line) in zip(histories, styles):
        epochs = [r["epoch"] + (parent_epoch if label == "Версия 10" else 0) for r in rows]
        losses = [r["loss"] for r in rows]
        errors = [100 * (r["at_0_5"]["fp"] + r["at_0_5"]["fn"])
                  / sum(r["at_0_5"][k] for k in COUNTS) for r in rows]
        assert all(math.isfinite(v) and v > 0 for v in losses)
        marks = [6, 11, 16, 19] if label == "Версия 9" else range(len(rows))
        for ax, values in zip(axes, (losses, errors)):
            ax.plot(epochs, values, label=label, color=color, marker=marker, markersize=4.5,
                    markevery=marks, linewidth=1.9, linestyle=line, markerfacecolor="white")
            ax.set_xlim(0.6, parent_epoch + len(histories[-1]) + 0.8)
            ax.set_xticks([1, 5, 7, 10, 15, 20, 25, 27])
            ax.set_xlabel("Эпоха, №")
    source = histories[-1][source_epoch - 1]
    branch = [dict(source, epoch=0), *continuation]
    extra_values = [[r["loss"] for r in branch],
                    [100 * (r["at_0_5"]["fp"] + r["at_0_5"]["fn"])
                     / sum(r["at_0_5"][k] for k in COUNTS) for r in branch]]
    parent = histories[2][parent_epoch - 1]
    first = histories[-1][0]
    parent_values = [parent["loss"], 100 * (parent["at_0_5"]["fp"] + parent["at_0_5"]["fn"])
                     / sum(parent["at_0_5"][k] for k in COUNTS)]
    first_values = [first["loss"], 100 * (first["at_0_5"]["fp"] + first["at_0_5"]["fn"])
                    / sum(first["at_0_5"][k] for k in COUNTS)]
    for ax, values, start, end in zip(axes, extra_values, parent_values, first_values):
        ax.annotate("", xy=(parent_epoch + 1, end), xytext=(parent_epoch, start),
                    arrowprops=dict(arrowstyle="->", color="#984f79", linewidth=1.3))
        ax.plot([parent_epoch + source_epoch + r["epoch"] for r in branch], values,
                label="Версия 10: дообучение", color="#984f79", marker="*", markevery=[1, 2],
                markersize=11, linewidth=1.9, linestyle="-", markerfacecolor="white", zorder=5)
    axes[0].set_yscale("log")
    axes[0].yaxis.set_major_formatter(FuncFormatter(lambda x, pos: fmt(x, max(0, -int(math.floor(math.log10(x)))))))
    axes[0].set_title("(а) Ошибка при обучении", pad=12, fontsize=17)
    axes[0].set_ylabel("Ошибка обучения, без единицы\n(шкала с шагом ×10)")
    axes[0].scatter([parent_epoch], [histories[2][parent_epoch - 1]["loss"]], s=180,
                    facecolors="none", edgecolors="#b47700", linewidths=1.4, zorder=4)
    axes[0].annotate("Старт версии 10", xy=(parent_epoch, histories[2][parent_epoch - 1]["loss"]),
                     xytext=(8.0, 0.025), fontsize=14,
                     arrowprops=dict(arrowstyle="->", color="#777777", linewidth=0.9))
    axes[0].scatter([parent_epoch + source_epoch], [source["loss"]], s=180,
                    facecolors="none", edgecolors="#984f79", linewidths=1.4, zorder=4)
    axes[0].annotate(f"Возврат к эпохе {source_epoch} версии 10", xy=(parent_epoch + source_epoch, source["loss"]),
                     xytext=(16.0, 0.025), fontsize=14,
                     arrowprops=dict(arrowstyle="->", color="#777777", linewidth=0.9))
    axes[1].set_title("(б) Ошибки на проверочных кадрах", pad=12, fontsize=17)
    axes[1].set_ylabel("Неверные ответы, %")
    axes[1].set_ylim(bottom=0)
    axes[1].yaxis.set_major_formatter(FuncFormatter(lambda x, pos: fmt(x, 1)))
    axes[1].text(0.98, 0.88, "Порог 0,5", transform=axes[1].transAxes, ha="right", fontsize=14)
    fig.suptitle("Полная история обучения моделей", y=0.98, fontsize=21)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", bbox_to_anchor=(0.55, 0.94),
               ncol=3, frameon=False, fontsize=14)
    fig.text(0.12, 0.11, "Счёт эпох версии 10 продолжает версию 9: основной запуск — позиции 8–27.\n"
             "Дообучение — ветка от эпохи 3 версии 10 (позиция 10): ещё 2 эпохи.\n"
             "Итоговые веса — последняя звёздочка на ветке дообучения. Меньше ошибок — лучше.\n"
             "Ошибка обучения — не процент; по вертикали соседние отметки отличаются в 10 раз.\n"
             "Данные у версий различаются. У версии 5 есть пересечение похожих изображений\n"
             "между обучением и проверкой, поэтому её оценка может быть завышена.", fontsize=14,
             va="center", linespacing=1.4)
    save(fig, "01_training_comparison")


def plot_matrices(metrics):
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 6.4))
    fig.subplots_adjust(left=0.13, right=0.98, bottom=0.25, top=0.8, wspace=0.42)
    for ax, split, title in zip(axes, ("valid", "test"), ("Проверочные кадры", "Тестовые кадры")):
        m = metrics[split]["thresholds"]["0.3"]
        counts = np.array([[m["tn"], m["fp"]], [m["fn"], m["tp"]]])
        percentages = 100 * counts / counts.sum(axis=1, keepdims=True)
        ax.set_xlim(-0.5, 1.5)
        ax.set_ylim(1.5, -0.5)
        ax.set_aspect("equal")
        ax.grid(False)
        ax.set_xticks([0, 1], ["Без спагетти", "Спагетти"])
        ax.set_yticks([0, 1], ["Без спагетти", "Спагетти"])
        ax.set_xlabel("Ответ модели", labelpad=9)
        ax.set_ylabel("Что на кадре", labelpad=9)
        ax.set_title(f"{title}\nКадров: {integer(int(counts.sum()))} шт.", fontsize=16, pad=12)
        for i in range(2):
            for j in range(2):
                ax.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1,
                                       facecolor=matplotlib.colormaps["Blues"](percentages[i, j] / 100),
                                       edgecolor="white", linewidth=1))
                ax.text(j, i, f"{integer(int(counts[i, j]))}\n{fmt(percentages[i, j])} %",
                        ha="center", va="center", color="white" if percentages[i, j] > 55 else "#222222",
                        fontsize=19, linespacing=1.4)
    fig.suptitle("Ответы итоговой версии 10", y=0.98, fontsize=21)
    fig.text(0.55, 0.885, "Порог решения: 0,3 (число от 0 до 1)", ha="center", fontsize=14)
    fig.text(0.055, 0.075, "В ячейках — число кадров, шт., и доля от всех кадров того же класса, %.\n"
             "Строка показывает, что было на кадре; столбец — ответ модели.", fontsize=14, linespacing=1.4)
    save(fig, "02_confusion_matrices")


def plot_sources(source_metrics):
    fig, axes = plt.subplots(1, 2, sharey=True, figsize=(14.0, 8.0))
    fig.subplots_adjust(left=0.32, right=0.98, bottom=0.25, top=0.8, wspace=0.23)
    labels = []
    for name, m in source_metrics.items():
        labels.append(f"{SOURCES[name]}\nсо спагетти: {integer(m['tp'] + m['fn'])} шт.; "
                      f"без: {integer(m['fp'] + m['tn'])} шт.")
    for ax, key, title, color in zip(axes, ("recall", "false_alarm_rate"),
                                   ("Сколько дефектов найдено", "Ложные срабатывания"), ("#376c9a", "#b47700")):
        for i, m in enumerate(source_metrics.values()):
            value = m[key]
            if value is None:
                ax.text(3, i, "—", va="center", fontsize=15)
                continue
            percentage = 100 * value
            ax.barh(i, percentage, height=0.46, color=color, alpha=0.88)
            if percentage == 0:
                ax.plot(0, i, "o", color=color, markersize=4, clip_on=False)
            ax.text(percentage + 2, i, f"{fmt(percentage, 1)} %", va="center", fontsize=14)
        ax.set_xlim(0, 121)
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.set_xlabel("Доля кадров, %")
        ax.set_title(title, pad=12, fontsize=17)
        ax.grid(axis="y", visible=False)
        ax.set_axisbelow(True)
    axes[0].set_yticks(range(len(labels)), labels, fontsize=14)
    axes[0].set_ylim(len(labels) - 0.5, -0.5)
    axes[1].tick_params(axis="y", left=False)
    fig.suptitle("Как версия 10 распознаёт разные группы кадров", y=0.98, fontsize=21)
    fig.text(0.65, 0.9, "Порог 0,3 (от 0 до 1); всего 3 337 кадров", ha="center", fontsize=14)
    fig.text(0.035, 0.065,
             "Слева — найденные кадры со спагетти от всех кадров со спагетти в группе, %.\n"
             "Справа — ложные срабатывания от всех кадров без спагетти в группе, %.\n"
             "Прочерк — в группе нет нужного класса. При малом числе кадров один ответ сильно меняет процент.\n"
             "Кадры посчитаны один раз; пересекающиеся группы исключены.",
             fontsize=14, linespacing=1.4)
    save(fig, "03_quality_by_source")


def write_tables(rows, font):
    headers = ["Группа данных", "Источник / сессия", "Порог", "Кадров", "С дефектом", "Без дефекта",
               "TP", "FP", "FN", "TN", "Точность положительных ответов, %", "Полнота, %", "F1, %",
               "Доля верных ответов, %", "AP, %", "Доля ложных тревог, %", "Источник результата"]
    table = []
    for group, name, m, evidence in rows:
        f1 = m["f1"] if 2 * m["tp"] + m["fp"] + m["fn"] else None
        values = [m.get(k) for k in RATE_KEYS]
        values[2] = f1
        counts = [sum(m[k] for k in COUNTS), m["tp"] + m["fn"], m["fp"] + m["tn"]]
        table.append([group, name, "0,3", *counts, *(m[k] for k in COUNTS),
                      *(fmt(None if v is None else v * 100) for v in values), evidence])
    with (OUT / "metrics_v10.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream, delimiter=";")
        writer.writerow(headers)
        writer.writerows(table)
    columns = [0, 1, 3, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    titles = ["Выборка", "Группа", "Кадров", "TP", "FP", "FN", "TN", "Точность, %", "Полнота, %",
              "F1, %", "Верные ответы, %", "AP, %", "Ложные тревоги, %"]
    lines = ["# Метрики итоговой версии 10", "", "ResNet18, полный кадр 384 × 384. Порог обнаружения — 0,3.", ""]
    for group, heading in [("Контроль", "Контрольные выборки"), ("Диагностика обучения", "Четыре добавленные обучающие сессии"),
                           ("Источники теста", "Тест по источникам кадров")]:
        lines.extend([f"## {heading}", "", "| " + " | ".join(titles) + " |",
                      "| " + " | ".join(["---"] * len(titles)) + " |"])
        for row in table:
            if row[0] != group:
                continue
            formatted = [integer(row[i]) if isinstance(row[i], int) else str(row[i]) for i in columns]
            lines.append("| " + " | ".join(formatted) + " |")
        lines.append("")
    lines.extend([
        "TP — обнаруженный дефект; FP — ложная тревога; FN — пропущенный дефект; TN — кадр без дефекта и без тревоги.", "",
        "Точность = TP / (TP + FP); полнота = TP / (TP + FN); F1 = 2TP / (2TP + FP + FN); доля верных ответов = (TP + TN) / N; доля ложных тревог = FP / (FP + TN). AP характеризует ранжирование score и не зависит от выбранного порога.", "",
        "Прочерк означает, что показатель не определён либо AP не сохранена для данного среза. При TP = FP = FN = 0 в исходных JSON F1 записана как 0; в таблице стоит прочерк, поскольку её знаменатель равен нулю. Числа округлены до двух знаков, расчёты выполнены без округления.", "",
        "## Интерпретация и ограничения", "",
        "- Общий тест: 917 обнаруженных дефектов, 13 ложных тревог, один пропуск и 2 406 верных отрицательных ответов. Исторический тест самого принтера: 13 из 14 дефектных кадров обнаружены, три ложные тревоги на 459 отрицательных кадрах.",
        "- На исторической валидации самого принтера пропущены все пять положительных кадров. Высокая доля верных ответов здесь определяется преобладанием отрицательных кадров.",
        "- Четыре добавленные сессии входят в обучение. Обнаружены все 21 положительный кадр; ложных тревог на 94 отрицательных кадрах нет. Это проверка усвоения обучающих данных, а не независимая оценка качества.",
        "- Сохранённые контрольные наборы многократно использовались при разработке. Кадры одной печати коррелированы; для оценки переноса нужны новые целые сессии вне обучения. Эти результаты не подтверждают обнаружение спагетти при 5D-печати.",
        "- На сборном рисунке показаны разные эксперименты, составы данных и начальные веса. Снижение функции потерь не доказывает превосходство одной версии над другой. У версии 5 подтверждено пересечение преобразованных изображений между обучением и валидацией.",
        "- Доля ошибок по эпохам рассчитана при пороге 0,5 из сохранённых записей истории. Итоговые таблицы, матрицы и сравнение источников используют порог 0,3.",
        "- На общей оси графика счёт версии 10 продолжается от эпохи 7 версии 9: двадцать эпох основного запуска занимают позиции 8–27. Стрелка связывает исходные веса v9 на позиции 7 с первой обученной эпохой v10 на позиции 8; исходная ошибка на позиции 7 относится к v9, а не к новому измерению v10. Две эпохи дообучения показаны отдельной веткой от эпохи 3 версии 10, то есть от позиции 10 общей оси; новые точки ветки находятся на позициях 11 и 12. Для дообучения оптимизатор создан заново. Последняя звёздочка — итоговые веса: 3 + 2 = 5 эпох поверх версии 9, всего выполнено 22 эпохи; ветка не соединена с концом основного запуска.",
        "- Ошибка обучения — бинарная перекрёстная энтропия, без единицы измерения. На графике её шкала логарифмическая: соседние основные отметки отличаются в 10 раз. Неверные ответы и доли распознавания указаны в процентах; объём групп — в кадрах. Весь текст рисунков имеет размер не меньше 14 pt.",
        "- Срез reviewed_hard_negatives пересекается с источниками и не добавляется к их сумме. AP для отдельных источников и отдельных обучающих сессий не была сохранена; в таблице она не подменяется новым расчётом.", "",
        "## Исходные материалы", "",
    ])
    for path in INPUT_HASHES:
        source = Path(path)
        lines.append(f"- [{source.parent.name}/{source.name}]({source.as_posix()})")
    lines.extend(["", "## Рисунки и повторное построение", "",
                  "- 01_training_comparison — динамика обучения четырёх версий, две панели.",
                  "- 02_confusion_matrices — матрицы ошибок валидации и теста.",
                  "- 03_quality_by_source — полнота и ложные тревоги по источникам тестовых кадров.", "",
                  "Каждый рисунок сохранён в PNG 300 dpi и векторном PDF со встроенным Times New Roman, текст не меньше 14 pt. "
                  "Проверки данных, шрифтов, границ подписей и формата экспортов записаны в verification.json.", "",
                  "Для повторного построения запустите из корня Nir2:", "", "```powershell",
                  "python outputs/model_v10_report/render_report.py", "```", "",
                  "Нужны NumPy, Matplotlib, Pillow и установленный Times New Roman. Скрипт читает сохранённые JSON "
                  "из соседнего printer-defect-server и пишет только в свой каталог; модель и изображения не загружает.", "",
                  f"Использованный файл шрифта: `{font}`."])
    (OUT / "metrics_v10.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(table)


def main():
    font = font_manager.findfont("Times New Roman", fallback_to_default=False)
    assert font_manager.FontProperties(fname=font).get_name() == "Times New Roman"
    plt.rcParams.update({"font.family": "Times New Roman", "font.size": 14,
                         "axes.grid": True, "grid.alpha": 0.2, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.unicode_minus": False,
                         "pdf.fonttype": 42, "ps.fonttype": 42, "figure.facecolor": "white"})
    metrics = read(V10 / "classification_metrics.json")
    predictions = read(V10 / "classification_predictions.json")
    metadata = read(V10 / "run_metadata.json")
    diagnostics = read(V10 / "training_diagnostics_metrics.json")
    train_predictions = read(V10 / "training_diagnostics_predictions.json")
    rows = []
    for split, name in [("valid", "Валидация, весь набор"), ("test", "Тест, весь набор")]:
        assert len(predictions[split]) == metadata["splits"][split]["images"]
        m = dict(metrics[split]["thresholds"]["0.3"], image_AP=metrics[split]["image_AP"])
        verify(predictions[split], m)
        assert m["tp"] + m["fn"] == metadata["splits"][split]["positive"]
        assert m["fp"] + m["tn"] == metadata["splits"][split]["negative"]
        rows.append(("Контроль", name, m, f"classification_metrics.json: {split}"))
        target = [r for r in predictions[split] if r["origin"].startswith("printer_")]
        target_m = metadata["target_metrics_at_0_3"][split]
        verify(target, target_m)
        assert target_m["tp"] + target_m["fn"] == metadata["splits"][split]["printer_labels"]["1"]
        assert target_m["fp"] + target_m["tn"] == metadata["splits"][split]["printer_labels"]["0"]
        rows.append(("Контроль", "Историческая " + ("валидация принтера" if split == "valid" else "тестовая выборка принтера"),
                     target_m, f"run_metadata.json: target_metrics_at_0_3.{split}"))
    assert diagnostics["usage"] == "training_diagnostics_only" and diagnostics["threshold"] == THRESHOLD
    verify(train_predictions, diagnostics["overall"])
    rows.append(("Диагностика обучения", "Все четыре сессии", diagnostics["overall"], "training_diagnostics_metrics.json: overall"))
    for session, m in diagnostics["sessions"].items():
        selected = [r for r in train_predictions if r["session"] == session]
        verify(selected, m)
        assert all(r["threshold"] == THRESHOLD and r["spaghetti"] == (r["score"] >= THRESHOLD) for r in selected)
        rows.append(("Диагностика обучения", session, m, f"training_diagnostics_metrics.json: sessions.{session}"))
    source_metrics = {}
    assert {r["origin"] for r in predictions["test"]} == set(SOURCES)
    for source, label in SOURCES.items():
        selected = [r for r in predictions["test"] if r["origin"] == source]
        published = metrics["test"]["slices"][source]["thresholds"]["0.3"]
        verify(selected, published)
        source_metrics[source] = published
        rows.append(("Источники теста", label.replace("\n", " "), published, f"classification_metrics.json: test.slices.{source}"))
    assert sum(sum(m[k] for k in COUNTS) for m in source_metrics.values()) == len(predictions["test"])
    assert all(sum(m[k] for m in source_metrics.values()) == metrics["test"]["thresholds"]["0.3"][k] for k in COUNTS)
    histories = [read(MODELS / f"spaghetti_presence_{v}" / "history.json") for v in ("v5", "v8_r4", "v9")]
    initial = read(V10 / "first_stage_history.json")
    continuation = read(V10 / "history.json")
    config = read(V10 / "training_config.json")
    parent_metadata = read(MODELS / "spaghetti_presence_v9" / "run_metadata.json")
    assert metadata["parent_checkpoint_sha256"] == parent_metadata["checkpoint_sha256"]
    parent_epoch = parent_metadata["best_epoch"]
    assert parent_epoch == 7
    offset = config["sampler_epoch_offset"]
    assert offset == metadata["continuation"]["sampler_epoch_offset"] == 3
    assert len(initial) == 20 and len(continuation) == 2
    assert len(initial) + len(continuation) == metadata["completed_training_epochs"] == 22
    assert metadata["best_epoch"] == 2 and metadata["effective_epoch"] == offset + 2 == 5
    final_chain = initial[:offset] + [dict(r, epoch=r["epoch"] + offset) for r in continuation]
    histories.append(initial)
    for history in histories + [continuation]:
        assert [r["epoch"] for r in history] == list(range(1, len(history) + 1))
        for r in history:
            m = r["at_0_5"]
            n = sum(m[k] for k in COUNTS)
            assert math.isclose((m["tp"] + m["tn"]) / n, m["accuracy"], abs_tol=1e-12)
    # Отрицательный контроль: проверка должна отвергнуть неверную матрицу.
    bad = dict(metrics["test"]["thresholds"]["0.3"])
    bad["fp"] += 1
    try:
        verify(predictions["test"], bad)
    except AssertionError:
        pass
    else:
        raise AssertionError("Сверка не обнаружила изменённое число ложных тревог")
    plot_history(histories, continuation, parent_epoch, offset)
    plot_matrices(metrics)
    plot_sources(source_metrics)
    row_count = write_tables(rows, font)
    assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest() == sha for path, sha in INPUT_HASHES.items())
    verification = dict(threshold=THRESHOLD, metric_rows=row_count, font_file=font,
                        predictions_reconciled=True, negative_control_passed=True,
                        formulas_checked=True, disjoint_test_sources_reconciled=True,
                        final_v10_chain_epochs=[r["epoch"] for r in final_chain],
                        plotted_v10_main_epochs=[r["epoch"] for r in initial],
                        plotted_v10_continuation_epochs=[r["epoch"] for r in continuation],
                        plotted_v10_main_positions=[parent_epoch + r["epoch"] for r in initial],
                        plotted_v10_continuation_positions=[parent_epoch + offset + r["epoch"] for r in continuation],
                        v10_parent=dict(version="v9", epoch=parent_epoch),
                        v10_continuation_origin=dict(version="v10", epoch=offset),
                        completed_v10_training_epochs=22, figures=FIGURES,
                        input_sha256=INPUT_HASHES, source_files_unchanged=True)
    (OUT / "verification.json").write_text(json.dumps(verification, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"REPORT VERIFIED: {row_count} metric rows; 3 PNG + 3 vector PDF; Times New Roman")


if __name__ == "__main__":
    main()
