import obspython as obs
import mpd

address = ""
port = 0
password = ""
interval = 1000
source_name = ""
verbose = False

initialized = False

signal_handler = None

mpd_client = mpd.MPDClient()


def script_description():
    return "Starts MPD playback when specific text source activates and updates its contents with the current song info. Playback is stopped when the source deactivates.\n\ngithub.com/ansse/OBS-MPD-Client"

def mpd_connected():
    global mpd_client
    global verbose

    reply = None
    ret = False
    try:
        mpd_client.ping()
        ret = True
        if verbose:
            print("Got a ping reply from MPD.")
    except mpd.ConnectionError as e:
        ret = False
        if verbose:
            print("Not connected to MPD")
    except Exception as e:
            print("WARN: Pinging MPD failed:\n".format(address, port, e))

    return ret

def connect_mpd():
    global address
    global password
    global port
    global mpd_client

    disconnect_mpd()

    if verbose:
        print("Connecting to MPD at {}:{}".format(address,port))
    mpd_client.timeout = 1
    try:
        mpd_client.connect(address, port)
        mpd_client.password(password)
    except Exception as e:
        print("ERROR: Connection to {}:{} failed:\n{}".format(address, port, e))
        mpd_client.disconnect()
        return False
    return True


def disconnect_mpd():
    global mpd_client
    mpd_client.disconnect()


def initialize_mpd():
    return

def reconnect_pressed(props, prop):

    connect_mpd()
    initialize_mpd()


def update_text():
    global interval
    global source_name

    source = obs.obs_get_source_by_name(source_name)
    if source is not None:
        text = ""

        if not mpd_connected() and not connect_mpd():
            print("WARN: Connection to MPD lost. Clearing the text source")
            text = ""
        else:
            text = "{artist}\n{title}".format(**mpd_client.currentsong())


        settings = obs.obs_data_create()
        obs.obs_data_set_string(settings, "text", text)
        obs.obs_source_update(source, settings)
        obs.obs_data_release(settings)

        obs.obs_source_release(source)


def script_properties():
    props = obs.obs_properties_create()

    obs.obs_properties_add_text(props, "address", "MPD address", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_int(props, "port", "MPD port number", 1, 65353, 1)
    obs.obs_properties_add_text(props, "password", "MPD password", obs.OBS_TEXT_PASSWORD)

    obs.obs_properties_add_button(props, "reconnect", "Reconnect and reset", reconnect_pressed)

    obs.obs_properties_add_int(props, "interval", "Text update interval (milliseconds)", 100, 10000, 100)

    p = obs.obs_properties_add_list(props, "source", "Text source", obs.OBS_COMBO_TYPE_EDITABLE,
                                    obs.OBS_COMBO_FORMAT_STRING)
    sources = obs.obs_enum_sources()
    if sources is not None:
        for source in sources:
            source_id = obs.obs_source_get_id(source)
            if source_id == "text_gdiplus" or source_id == "text_ft2_source":
                name = obs.obs_source_get_name(source)
                obs.obs_property_list_add_string(p, name, name)

        obs.source_list_release(sources)

    obs.obs_properties_add_bool(props, "verbose", "Verbose logging")

    return props


def script_defaults(settings):
    obs.obs_data_set_default_bool(settings, "verbose", False)
    obs.obs_data_set_default_int(settings, "interval", 1000)
    obs.obs_data_set_default_int(settings, "port", 6600)
    obs.obs_data_set_default_string(settings, "password", "")


def script_update(settings):
    global address
    global port
    global password
    global interval
    global source_name
    global verbose
    global initialized

    if verbose:
        print("Script updating.")

    verbose = obs.obs_data_get_bool(settings, "verbose")

    address = obs.obs_data_get_string(settings, "address")
    port = obs.obs_data_get_int(settings, "port")
    password = obs.obs_data_get_string(settings, "password")
    interval = obs.obs_data_get_int(settings, "interval")
    source_name = obs.obs_data_get_string(settings, "source")

    obs.timer_remove(update_text)

    if not initialized:
        connect_mpd()
        if mpd_connected():
            initialize_mpd()
            initialized = True

    if mpd_connected() and source_name != "":
        obs.timer_add(update_text, interval)



def source_activated(calldata):
    global verbose
    global source_name
    global initialized
    global mpd_client

    source = obs.calldata_source(calldata, "source")
    if source is not None and initialized:
        if source_name == obs.obs_source_get_name(source):
            if verbose:
                print("Source \"" + source_name + "\" activated. Sending the play command.")
            if not mpd_connected() and not connect_mpd():
                print("ERROR: Connection to MPD lost. Cannot send play command.")
            else:
                mpd_client.next()


def source_deactivated(calldata):
    global verbose
    global source_name
    global initialized
    global mpd_client

    source = obs.calldata_source(calldata, "source")
    if source is not None and initialized:
        if source_name == obs.obs_source_get_name(source):
            if verbose:
                print("Source \"" + source_name + "\" deactivated. Sending the stop command.")
            if not mpd_connected() and not connect_mpd():
                print("ERROR: Connection to MPD lost. Cannot send stop command.")
            else:
                mpd_client.pause(1)



def disconnect_handler():
    global signal_handler

    if signal_handler is not None:
        obs.signal_handler_disconnect(signal_handler, "source_activate", source_activated)
        obs.signal_handler_disconnect(signal_handler, "source_deactivate", source_deactivated)
    signal_handler = None


def connect_handler():
    global signal_handler

    disconnect_handler()

    signal_handler = obs.obs_get_signal_handler()
    obs.signal_handler_connect(signal_handler, "source_activate", source_activated)
    obs.signal_handler_connect(signal_handler, "source_deactivate", source_deactivated)


def script_load(settings):
    print("Script loading.")
    connect_handler()


def script_unload():
    global initialized
    initialized = False
    print("Script unloading.")
    disconnect_mpd()
    disconnect_handler()
