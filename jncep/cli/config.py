import shutil

import click

from .. import config, track, utils
from .base import CatchAllExceptionsCommand

console = utils.getConsole()


@click.group(name="config", help="Manage configuration")
def config_manage():
    pass


@config_manage.command(
    name="show", help="List configuration details", cls=CatchAllExceptionsCommand
)
def config_list():
    config_dir = config.config_dir()
    if not config_dir.exists():
        console.warning("No suitable configuration directory found!")
        console.info(f"The recommended location is: [highlight]{config_dir}[/]")
        return

    if not config_dir.is_dir:
        console.warning(f"Not a directory: [highlight]{config_dir}[/]")

    console.info(f"Config directory: [highlight]{config_dir}[/]")
    files = list(config_dir.iterdir())
    for f_ in files:
        if f_.is_file():
            if f_.name == track.TRACK_FILE_NAME:
                console.info(f"Found tracking file: [highlight]{f_.name}[/]")
                _track_file_summary(f_)
                continue
            if f_.name == config.CONFIG_FILE_NAME:
                console.info(f"Found config file: [highlight]{f_.name}[/]")
                _config_file_summary(f_)
                continue
        # ignore everything else


def _track_file_summary(file_path):
    track_config_manager = track.TrackConfigManager(file_path)
    tracked_series = track_config_manager.read_tracked_series()
    len_ts = len(tracked_series)
    console.info(f"{len_ts} series tracked")


def _config_file_summary(file_path):
    config_manager = config.ConfigManager(file_path)
    config_options = config_manager.read_config_options()
    # TOP_SECTION is always there (default section)
    jncep_s = config_options[config.TOP_SECTION]
    # ignore other non listed in OPTIONS
    for option in config.list_available_config_options():
        if option not in jncep_s:
            continue
        console.info(f"Option: [highlight]{option}[/] => [green]{jncep_s[option]}[/]")


@config_manage.command(
    name="set", help="Set configuration option", cls=CatchAllExceptionsCommand
)
@click.argument("option", metavar="OPTION", required=True)
@click.argument("value", metavar="VALUE", required=True)
def set_option(option, value):
    config_manager = config.ConfigManager()
    config_options = config_manager.read_config_options()

    option = config.set_config_option(config_options, option, value)
    console.info(
        f"Option '[highlight]{option}[/]' set to '[highlight]{value}[/]'",
        style="success",
    )

    is_needs_created = not config_manager.config_file_path.exists()
    # if config file didn't exist, this will create it
    config_manager.write_config_options(config_options)
    if is_needs_created:
        # mention the creation to user
        console.info(
            f"Config file created at: [highlight]{config_manager.config_file_path}[/]"
        )


@config_manage.command(
    name="unset", help="Delete configuration option", cls=CatchAllExceptionsCommand
)
@click.argument("option", metavar="OPTION", required=True)
def unset_option(option):
    config_manager = config.ConfigManager()

    if not config_manager.config_file_path.exists():
        console.warning(
            f"No config file found at: [highlight]{config_manager.config_file_path}[/]"
        )
        return

    config_options = config_manager.read_config_options()

    option, is_deleted = config.unset_config_option(config_options, option)
    if not is_deleted:
        console.warning(f"Option '[highlight]{option}[/]' not set in config")
        return
    else:
        console.info(f"Option '[highlight]{option}[/]' unset", style="success")

    config_manager.write_config_options(config_options)


@config_manage.command(
    name="init", help="Create configuration file", cls=CatchAllExceptionsCommand
)
def init_config():
    config_filepath = config.DEFAULT_CONFIG_FILEPATH
    if config_filepath.exists():
        console.warning(f"Config file already exists: [highlight]{config_filepath}[/]")
        return

    config_manager = config.ConfigManager(config_filepath)
    # will create empty config file
    config_options = config_manager.read_config_options()
    config_manager.write_config_options(config_options)

    console.info(
        f"New empty config file created: [highlight]{config_filepath}[/]",
        style="success",
    )


@config_manage.command(
    name="migrate",
    help=f"Migrate to standard configuration folder [{config.APPDATA_CONFIG_DIR}]",
    cls=CatchAllExceptionsCommand,
)
def config_migrate():
    current_config_dir = config.config_dir()
    if current_config_dir == config.APPDATA_CONFIG_DIR:
        console.warning(
            f"Configuration is already in: [highlight]{config.APPDATA_CONFIG_DIR}[/]"
        )
        return

    migrate_config_dir = config.APPDATA_CONFIG_DIR

    # configuration is in legacy_config_dir => migrate to appdir

    migrate_config_dir.mkdir(parents=True)

    from_track_filepath = current_config_dir / track.TRACK_FILE_NAME
    if from_track_filepath.exists():
        to_track_filepath = migrate_config_dir / track.TRACK_FILE_NAME
        shutil.copy2(from_track_filepath, to_track_filepath)

    from_config_filepath = current_config_dir / config.CONFIG_FILE_NAME
    if from_config_filepath.exists():
        to_config_filepath = migrate_config_dir / config.CONFIG_FILE_NAME
        shutil.copy2(from_config_filepath, to_config_filepath)

    console.info(
        "[success]"
        f"The configuration is now in: [highlight]{migrate_config_dir}[/]"
        "[/] "
        f"You may delete: [highlight]{current_config_dir}[/]"
    )
