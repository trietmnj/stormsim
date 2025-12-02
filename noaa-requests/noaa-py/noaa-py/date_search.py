def date_search(d_struct, d_beg, d_end, indx):
    invalid_flag = False

    range_start = d_struct['start_date'][indx]
    range_end = d_struct['end_date'][indx]

    range_start = [datetime.datetime.strptime(item[:19], "%Y-%m-%d %H:%M:%S") for item in range_start]
    range_end = [datetime.datetime.strptime(item[:19], "%Y-%m-%d %H:%M:%S") for item in range_end]

    u_bound_chk_dummy = [d_beg >= start and d_beg <= end for start, end in zip(range_start, range_end)]
    l_bound_chk_dummy = [d_end >= start and d_end <= end for start, end in zip(range_start, range_end)]

    dummy_indx = [u + l for u, l in zip(u_bound_chk_dummy, l_bound_chk_dummy)]

    if all(item == 0 for item in dummy_indx):
        invalid_flag = True
    elif any(item == 2 for item in dummy_indx):
        indx = [i for i, value in enumerate(dummy_indx) if value == 2]
    elif any(item == 1 for item in dummy_indx):
        if all(u == 0 for u in u_bound_chk_dummy):
            nearest_start = min(range_start, key=lambda x: abs(x - d_beg))
            d_beg = nearest_start
        elif all(l == 0 for l in l_bound_chk_dummy):
            nearest_end = min(range_end, key=lambda x: abs(x - d_end))
            d_end = nearest_end

    return indx, d_end, d_beg, invalid_flag

