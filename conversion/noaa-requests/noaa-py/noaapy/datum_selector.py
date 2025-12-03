def datum_selector(d_struct, requested_datum):
    dummy = [datum['name'] for datum in d_struct['datums']]

    try:
        dummyp = [datum['name'] for datum in d_struct['datums_predictions']]
    except KeyError:
        dummyp = True if "Great Lakes Gauge. No Tidal Predictions" in d_struct['datums_predictions'] else False
        if not dummyp:
            dummyp = "No Tidal Predictions" in d_struct['datums_predictions']

    prefered_datum = ['GL_LWD', 'NAVD88', 'MSL', 'MLLW'] if 'NAVD' in requested_datum else ['GL_LWD', 'MSL', 'MLLW', 'NAVD88']

    logical_matrix = [[case == datum for case in prefered_datum] for datum in dummy]

    if any(row[0] for row in logical_matrix) or dummyp:
        datum = 'IGLD'
        flag2 = True
    else:
        flag2 = False
        datum = next((pref for row, pref in zip(logical_matrix, prefered_datum) if any(row)), 'STND')

    if flag2:
        datum_p = 'No Tidal Predictions'
    else:
        dummy = ['NAVD88', 'MSL', 'MLLW'] if 'NAVD' in requested_datum else ['MSL', 'MLLW', 'NAVD88']
        logical_matrix_p = [[case == datum for case in dummy] for datum in dummy]
        datum_p = next((pref for row, pref in zip(logical_matrix_p, dummy) if any(row)), 'Prefered Datums Not Found')

    return datum, datum_p, flag2

