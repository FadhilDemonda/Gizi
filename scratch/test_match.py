item_options = ["Ati Ampela", "Buavita", "Bear Brand", "Yakult", "Puding", "Susu Ultra Mini", "Le Mineral 330", "Snack", "Pocari", "Buah"]

default_names = ["Buah", "Le Mineral 330", "Snack", "Pocari", "Buavita", "Bear Brand", "Yakult", "Puding", "Susu Ultra Mini"]

valid_defaults = []
for d in default_names:
    match = None
    for item in item_options:
        if str(item).lower() == d.lower():
            match = item; break
    if not match:
        for item in item_options:
            if str(item).lower().startswith(d.lower()):
                match = item; break
    if not match:
        for item in item_options:
            if d.lower() in str(item).lower():
                match = item; break
    if match:
        valid_defaults.append(match)

print(valid_defaults)
