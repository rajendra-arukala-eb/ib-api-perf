def build_list_params(pag_cfg: dict, page_index: int) -> dict:
    mode = pag_cfg.get("mode", "page_size")
    if mode == "offset_limit":
        size = int(pag_cfg.get("page_size", 2000))
        return {
            pag_cfg.get("offset_param", "offset"): page_index * size,
            pag_cfg.get("limit_param", "limit"): size,
        }
    page_param = pag_cfg.get("page_param", "page")
    size_param = pag_cfg.get("size_param", "size")
    one_based = bool(pag_cfg.get("page_one_based", False))
    page_num = page_index + 1 if one_based else page_index
    return {page_param: page_num, size_param: int(pag_cfg.get("page_size", 2000))}


def build_update_body(level: int) -> dict:
    return {"title": f"SDE-{level}"}


def build_create_body(name: str, dept: str) -> dict:
    return {"name": name, "dept": dept}
