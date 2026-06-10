"""
Utility functions shared across shape2instrument modules.
"""


def generate_wellplate_ids(n):
    """
    Generate n well-plate-style IDs (A1, B1, C1, ..., H12, A13, ...).

    Rows cycle A-H (8 rows), columns increment (1, 2, 3, ...).
    Supports any number of IDs beyond 96 by continuing into A13, B13, etc.

    Parameters
    ----------
    n : int
        Number of unique IDs to generate.

    Returns
    -------
    list of str
        List of n well-plate-style ID strings.
    """
    ids = []
    for i in range(n):
        row = i % 8
        col = i // 8
        ids.append(f"{chr(65 + row)}{col + 1}")
    return ids
