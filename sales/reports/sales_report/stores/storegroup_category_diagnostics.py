from __future__ import annotations
import pandas as pd


def build_yoy_storegroup_category(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Возвращает DataFrame уровня:
      storegroup_name, root_cat_name, cat_name,
      prev, curr, delta, delta_pct,
      prev_qty, curr_qty, delta_qty, delta_qty_pct
    """
    cols_out = [
        "storegroup_name", "root_cat_name", "cat_name",
        "prev", "curr", "delta", "delta_pct",
        "prev_qty", "curr_qty", "delta_qty", "delta_qty_pct",
    ]

    if df_raw is None or df_raw.empty:
        return pd.DataFrame(columns=cols_out)

    df = df_raw.copy()

    need = {"year", "storegroup_name", "cat_name", "amount"}
    if not need.issubset(df.columns):
        return pd.DataFrame(columns=cols_out)

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["quant"] = pd.to_numeric(df.get("quant"), errors="coerce").fillna(0.0)

    df["storegroup_name"] = df["storegroup_name"].fillna("Без группы").astype(str)
    df["cat_name"] = df["cat_name"].fillna("Без категории").astype(str)

    # root category (нулевой родитель)
    df["root_cat_name"] = df.get("root_cat_name")
    df["root_cat_name"] = df["root_cat_name"].fillna(df["cat_name"]).fillna("Без категории").astype(str)

    g = (
        df.groupby(["year", "storegroup_name", "root_cat_name", "cat_name"], as_index=False)
          .agg(amount=("amount", "sum"), quant=("quant", "sum"))
    )

    years = sorted(g["year"].dropna().unique())
    if len(years) < 2:
        return pd.DataFrame(columns=cols_out)

    y_prev, y_curr = years[-2], years[-1]

    p = (
        g[g["year"] == y_prev]
        .rename(columns={"amount": "prev", "quant": "prev_qty"})
        .drop(columns=["year"])
    )
    c = (
        g[g["year"] == y_curr]
        .rename(columns={"amount": "curr", "quant": "curr_qty"})
        .drop(columns=["year"])
    )

    out = p.merge(c, on=["storegroup_name", "root_cat_name", "cat_name"], how="outer").fillna(0.0)

    out["delta"] = out["curr"] - out["prev"]
    out["delta_pct"] = out.apply(lambda r: (r["delta"] / r["prev"] * 100) if r["prev"] else None, axis=1)

    out["delta_qty"] = out["curr_qty"] - out["prev_qty"]
    out["delta_qty_pct"] = out.apply(
        lambda r: (r["delta_qty"] / r["prev_qty"] * 100) if r["prev_qty"] else None,
        axis=1
    )

    out = out.sort_values("delta").reset_index(drop=True)
    out.attrs["y_prev"] = int(y_prev)
    out.attrs["y_curr"] = int(y_curr)
    return out


def top_drops(yoy_df: pd.DataFrame, n: int = 15) -> pd.DataFrame:
    """
    Топ N падений среди storegroup×category по delta (самые отрицательные).
    """
    if yoy_df is None or yoy_df.empty:
        return pd.DataFrame(columns=yoy_df.columns if yoy_df is not None else [])
    return yoy_df.sort_values("delta").head(n).copy()


def build_delta_matrix(yoy_df: pd.DataFrame, top_cats: int = 12, top_groups: int = 12) -> pd.DataFrame:
    """
    Матрица Δ₽: строки = группы, колонки = категории.
    """
    if yoy_df is None or yoy_df.empty:
        return pd.DataFrame()

    g_imp = (
        yoy_df.groupby("storegroup_name")["delta"]
        .sum()
        .abs()
        .sort_values(ascending=False)
        .head(top_groups)
        .index
    )
    c_imp = (
        yoy_df.groupby("cat_name")["delta"]
        .sum()
        .abs()
        .sort_values(ascending=False)
        .head(top_cats)
        .index
    )

    cut = yoy_df[
        yoy_df["storegroup_name"].isin(g_imp) &
        yoy_df["cat_name"].isin(c_imp)
    ].copy()

    mat = (
        cut.pivot_table(
            index="storegroup_name",
            columns="cat_name",
            values="delta",
            aggfunc="sum",
            fill_value=0.0
        )
    )

    mat["_sum"] = mat.sum(axis=1)
    mat = mat.sort_values("_sum").drop(columns=["_sum"])

    col_sum = mat.sum(axis=0).sort_values()
    mat = mat[col_sum.index]

    return mat


def build_delta_matrices_by_root(
    yoy_df: pd.DataFrame,
    top_roots: int = 6,
    top_cats_per_root: int = 8,
    top_groups: int = 12,
    min_abs_total: float = 1.0,
) -> list[tuple[str, pd.DataFrame]]:
    """
    Делает несколько матриц Δ₽ по root_cat_name (нулевой родитель):
      [(root_name, mat_df), ...]
    """
    if yoy_df is None or yoy_df.empty:
        return []
    if "root_cat_name" not in yoy_df.columns:
        return []

    root_scores = (
        yoy_df.groupby("root_cat_name")["delta"]
        .sum()
        .abs()
        .sort_values(ascending=False)
    )
    root_scores = root_scores[root_scores >= float(min_abs_total)]
    root_imp = list(root_scores.head(top_roots).index)

    matrices: list[tuple[str, pd.DataFrame]] = []

    for root in root_imp:
        cut_root = yoy_df[yoy_df["root_cat_name"] == root].copy()
        if cut_root.empty:
            continue

        # top cats внутри root
        c_imp = (
            cut_root.groupby("cat_name")["delta"]
            .sum()
            .abs()
            .sort_values(ascending=False)
            .head(top_cats_per_root)
            .index
        )

        # top storegroups внутри root
        g_imp = (
            cut_root.groupby("storegroup_name")["delta"]
            .sum()
            .abs()
            .sort_values(ascending=False)
            .head(top_groups)
            .index
        )

        cut = cut_root[
            cut_root["cat_name"].isin(c_imp) &
            cut_root["storegroup_name"].isin(g_imp)
        ].copy()

        mat = (
            cut.pivot_table(
                index="storegroup_name",
                columns="cat_name",
                values="delta",
                aggfunc="sum",
                fill_value=0.0
            )
        )

        if mat.empty:
            continue

        mat["_sum"] = mat.sum(axis=1)
        mat = mat.sort_values("_sum").drop(columns=["_sum"])

        col_sum = mat.sum(axis=0).sort_values()
        mat = mat[col_sum.index]

        matrices.append((str(root), mat))

    return matrices



def build_delta_qty_matrices_by_root(
    yoy_df: pd.DataFrame,
    top_roots: int = 6,
    top_cats_per_root: int = 8,
    top_groups: int = 12,
    min_abs_total: float = 1.0,
) -> list[tuple[str, pd.DataFrame]]:
    """
    То же самое, что build_delta_matrices_by_root, но для Δшт (delta_qty).
    Возвращает [(root_name, mat_df), ...]
    """
    if yoy_df is None or yoy_df.empty:
        return []
    if "root_cat_name" not in yoy_df.columns:
        return []
    if "delta_qty" not in yoy_df.columns:
        return []

    root_scores = (
        yoy_df.groupby("root_cat_name")["delta_qty"]
        .sum()
        .abs()
        .sort_values(ascending=False)
    )
    root_scores = root_scores[root_scores >= float(min_abs_total)]
    root_imp = list(root_scores.head(top_roots).index)

    matrices: list[tuple[str, pd.DataFrame]] = []

    for root in root_imp:
        cut_root = yoy_df[yoy_df["root_cat_name"] == root].copy()
        if cut_root.empty:
            continue

        # top cats внутри root по Δшт
        c_imp = (
            cut_root.groupby("cat_name")["delta_qty"]
            .sum()
            .abs()
            .sort_values(ascending=False)
            .head(top_cats_per_root)
            .index
        )

        # top storegroups внутри root по Δшт
        g_imp = (
            cut_root.groupby("storegroup_name")["delta_qty"]
            .sum()
            .abs()
            .sort_values(ascending=False)
            .head(top_groups)
            .index
        )

        cut = cut_root[
            cut_root["cat_name"].isin(c_imp) &
            cut_root["storegroup_name"].isin(g_imp)
        ].copy()

        mat = (
            cut.pivot_table(
                index="storegroup_name",
                columns="cat_name",
                values="delta_qty",
                aggfunc="sum",
                fill_value=0.0
            )
        )

        if mat.empty:
            continue

        mat["_sum"] = mat.sum(axis=1)
        mat = mat.sort_values("_sum").drop(columns=["_sum"])

        col_sum = mat.sum(axis=0).sort_values()
        mat = mat[col_sum.index]

        matrices.append((str(root), mat))

    return matrices