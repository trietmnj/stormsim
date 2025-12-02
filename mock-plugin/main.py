import cc.plugin_manager as manager

def __upload_data(pm):
    pm.copy_file_to_remote(
        manager.DataSourceOpInput(
            name="DamageFunctions", pathkey="default", datakey=None
        ),
        "/seed/damage-functions.json"
    )

def main():

    pm = manager.PluginManager()
    __upload_data(pm)
    print("StormSim finished running!!!")

if __name__ == "__main__":
    main()
