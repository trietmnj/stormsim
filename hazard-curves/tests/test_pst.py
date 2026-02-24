import numpy as np
import scipy.io as sio
import tables

from hazard_curves import StormSim_PST

data_fpath = "../matlab/SSv1.0_Forced_Sta50_2195_CHS-NA_SP6021.mat"

file = tables.open_file("data/processed_data.mat")
Nyrs_XC = file.root.Nyrs_XC[:][0, 0]
dcols = file.root.dcols[:][0, 0]
surge_pot = file.root.surge_pot[:]
file.close()


data = np.zeros((surge_pot.size, 3))
data[:, 1] = surge_pot.flatten()

test_data = {
    "random": sio.loadmat("./data/ecdf_random.mat")["rand_vals"],
    "indices": sio.loadmat("./data/ecdf_indices.mat")["idxs"] - 1,
}


if False:
    # Testing duplicates
    data = np.concatenate([data, data[:20, :]])
    # Testing flag values
    flag_values = [data[0, 1]]
else:
    flag_values = []

response = dict(
    data=data,
    flag_value=flag_values,
    SLC=0,
    Nyrs=Nyrs_XC * dcols,
    gprMdl=[],
    DataType="POT",
)

pst_options = dict(
    ind_Skew=0,
    use_AEP=0,
    prc=[16, 84],
    stat_print=1,
    tLag=0,
    GPD_TH_crit=2,
    apply_GPD_to_SS=1,
    bootstrap_sims=100,
)

plot_options = dict(
    create_plots=1, staID="SSL", yaxis_Label="Surge [m]", y_log=0, path_out=""
)

SST_Outputs, MRL_Output = StormSim_PST(
    response, pst_options, plot_options, test_ecdf_data=test_data
)


def err_stats(name, val, trg):
    print("==================")
    print(f"    {name}")
    error = np.abs((val - trg) / trg)
    print("--- Mean Error ---")
    print(np.nanmean(error, axis=0))
    print("--- Error Percentiles ---")
    print(np.nanpercentile(error, [50, 75, 90, 99], axis=0).T)


summary = sio.loadmat("./data/pst_summary.mat")["data"]
err_stats("Summary", summary, MRL_Output["summary"].values)

# selection = sio.loadmat("./data/pst_selection.mat")  # ["data"]

hc_plt_x = sio.loadmat("./data/pst_hc_plt_x.mat")["data"][:, 0]
err_stats("HC_plt_x", hc_plt_x, SST_Outputs["HC_plt_x"])

hc_plt = sio.loadmat("./data/pst_hc_plt.mat")["data"]
err_stats("HC_plt", hc_plt, SST_Outputs["HC_plt"])

hc_emp = sio.loadmat("./data/pst_hc_emp.mat")["data"]
err_stats("HC_emp", hc_emp, SST_Outputs["HC_emp"])

pd_k_wOut = sio.loadmat("./data/pst_pd_k_wOut.mat")["data"]
err_stats("pd_k_wOut", pd_k_wOut, MRL_Output["pd_k_wOut"])

pd_k_mod = sio.loadmat("./data/pst_pd_k_mod.mat")["data"]
err_stats("pd_k_mod", pd_k_mod, MRL_Output["pd_k_mod"])
