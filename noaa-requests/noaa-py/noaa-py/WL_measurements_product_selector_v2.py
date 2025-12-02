def wl_measurements_product_selector_v2(d_struct, prod):
    # Products List
    given = d_struct['WL_products']

    # Cases to Match
    want = [
        'Verified Monthly Mean Water Level',
        'Verified Hourly Height Water Level',
        'Verified 6-Minute Water Level',
        'Preliminary 6-Minute Water Level',
        'Verified High/Low Water Level'
    ]

    # Compute Logical Matrix (Columns Correspond To Cases In want)
    logical_matrix = [[case == given_item for case in want] for given_item in given]

    # Match the product flag
    if prod == want[0]:
        flag1 = 'm'
        col = 0
    elif prod == want[1]:
        flag1 = '1'
        col = 1
    elif prod == want[2]:
        flag1 = '6'
        col = 2
    elif prod == want[3]:
        flag1 = '6p'
        col = 3
    elif prod == want[4]:
        flag1 = 'hilo'
        col = 4
    else:
        raise ValueError("Product not recognized.")

    # Get Matching Indexes
    indx = [i for i, row in enumerate(logical_matrix) if row[col]]

    if not indx:
        flag2 = 1  # Product is not present in this station
    else:
        flag2 = 0

    return flag2, flag1, indx

