import matplotlib.pyplot as plt
from pathlib import Path

def plot_slr_curves(df, beta_values, wl_ds=None, title="Sea Level Rise Scenarios", line_names=None, output_folder=None):
    """
    Plots sea level rise curves with a custom legend.

    Args:
        df (pd.DataFrame): DataFrame with a 'year' column and scenario columns.
        beta_values (list): The list of beta values used to generate the curves.
        title (str): The title for the plot.
    """
    
    fig, ax = plt.subplots(figsize=(12, 8))

    # Get a list of just the scenario columns to iterate over
    scenario_cols = [col for col in df.columns if col != 'year']

    # Enumerate through the scenario columns to get an index (ii)
    for i, col_name in enumerate(scenario_cols):
        # The index 'i' corresponds to the index in the beta_values list
        # Create the custom label using an f-string
        if line_names is None:
            custom_label = f"Beta = {beta_values[i]} (col: {i+1})"
        else:
            custom_label = f"{line_names[i]}"
        
        ax.plot(df['year'], df[col_name]/1000, label=custom_label)

    if wl_ds is not None:
        # Get Keys 
        wl_keys = wl_ds.keys().to_list()
        # Plot Monthly Mean
        ax.plot(
            wl_ds[wl_keys[0]],       # The x-axis data
            wl_ds[wl_keys[1]],         # The y-axis data
            label='NOAA Monthly Mean', # Equivalent to 'name' in Plotly
            color='blue',         # Sets the line color
            linewidth=2           # Equivalent to line=dict(width=2)
            )
    
    
    # --- Customize the plot ---
    ax.set_xlabel("Year", fontsize=12)
    ax.set_ylabel("Cumulative Sea Level Rise (m)", fontsize=12)
    ax.set_title(title, fontsize=16, fontweight='bold')
    ax.legend()
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)

    plt.tight_layout()

    if output_folder is None:
        plt.show()  
    else:
        # Create PAth Obj 
        out_pth = Path(output_folder)
        # Create Directory) If Needed
        out_pth.mkdir(parents=True, exist_ok=True)
        # Print Figure
        fig.savefig(out_pth/'slr_projections.png', dpi=300, bbox_inches='tight')  
    