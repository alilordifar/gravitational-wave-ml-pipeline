import numpy as np
import logging

logger = logging.getLogger(__name__)


def normalize_strain(strain: np.ndarray) -> np.ndarray:
    mean = np.mean(strain)
    std = np.std(strain)

    if std == 0:
        raise ValueError("Standard deviation is zero, cannot normalize.")

    normalized_strain = (strain - mean) / std

    rows = [
        ("Statistic",        "Before",                          "After"),
        ("-" * 12,           "-" * 18,                          "-" * 18),
        ("Mean",             f"{mean:.6e}",                     f"{np.mean(normalized_strain):.6e}"),
        ("Std Dev",          f"{std:.6e}",                      f"{np.std(normalized_strain):.6e}"),
        ("Min",              f"{np.min(strain):.6e}",           f"{np.min(normalized_strain):.6e}"),
        ("Max",              f"{np.max(strain):.6e}",           f"{np.max(normalized_strain):.6e}"),
        ("Samples",          f"{strain.size}",                  f"{normalized_strain.size}"),
    ]

    col_w = [max(len(r[i]) for r in rows) for i in range(3)]
    line  = "+-{}-+-{}-+-{}-+".format(*("-" * w for w in col_w))

    table_lines = [line]
    for i, row in enumerate(rows):
        table_lines.append("| {} | {} | {} |".format(*(cell.ljust(col_w[j]) for j, cell in enumerate(row))))
        if i in (0, 1):
            table_lines.append(line)
    table_lines.append(line)

    logger.info("Strain normalization summary:\n" + "\n".join(table_lines))

    return normalized_strain
