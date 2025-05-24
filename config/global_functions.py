def is_planner_needed(has_lauched: bool) -> bool:
    if has_lauched:
        return False
    else:
        return True

func_map = {
    "is_planner_needed": is_planner_needed
}

