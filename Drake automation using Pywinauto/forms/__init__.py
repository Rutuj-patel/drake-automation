from forms.name_address  import open_or_create_return, fill_name_and_address
from forms.w2            import process_w2
from forms.form_1098     import process_1098
from forms.form_5498     import process_5498
from forms.form_1099_div import process_1099_div
from forms.form_8949     import process_8949
from forms.form_8889     import process_8889

__all__ = [
    "open_or_create_return",
    "fill_name_and_address",
    "process_w2",
    "process_1098",
    "process_5498",
    "process_1099_div",
    "process_8949",
    "process_8889",
]