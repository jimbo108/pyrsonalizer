def naive_object_comparison(obj_one: object, obj_two: object) -> bool:
    obj_one_attrs = [
        attr
        for attr in dir(obj_one)
        if not callable(getattr(obj_one, attr)) and not attr.startswith("__")
    ]
    obj_two_attrs = [
        attr
        for attr in dir(obj_two)
        if not callable(getattr(obj_one, attr)) and not attr.startswith("__")
    ]
    if set(obj_one_attrs) != set(obj_two_attrs):
        return False

    for attr in obj_one_attrs:
        if getattr(obj_one, attr) != getattr(obj_two, attr):
            return False

    return True
