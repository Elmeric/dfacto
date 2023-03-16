"""Entry point for the GUI version of fotocop.
"""
import sys
import os
import logging
from typing import TYPE_CHECKING, Optional
from enum import Enum


import PyQt6.QtCore as QtCore
import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtGui as QtGui

import dfacto.__about__ as __about__
from dfacto.util.logutil import LogConfig
from dfacto.util import qtutil as QtUtil
from dfacto.backend import db

# Models
from dfacto import settings as Config
from dfacto.backend import api, schemas
from dfacto.backend.api.command import CommandStatus
# from fotocop.models.sources import SourceManager, Source, ImageProperty, Device, LogicalDisk
# from fotocop.models.downloader import Downloader
# from fotocop.models.naming import Case, TemplateType

# Views
from dfacto.frontend.companydialogs import AddCompanyDialog, SelectCompanyDialog
# from .fileexplorer import FileSystemModel, FileSystemDelegate, FileSystemFilter
# from .sourceselector import SourceSelector
# from .thumbnailviewer import ThumbnailViewer
# from .timelineviewer import TimelineViewer
# from .renamepanel import RenamePanel
# from .destinationpanel import DestinationPanel
# from .download import DownloadButton, DownloadProgress
# from .sessioneditor import SessionEditor

# if TYPE_CHECKING:
#     from fotocop.models.sources import ImageKey

__all__ = ["qt_main"]

logger = logging.getLogger(__name__)


class QtMainView(QtWidgets.QMainWindow):
#     """The fotocop main view.
#
#     The Main view is composed of:
#         The source selector:  browse and select an images' source.
#         The thumbnail viewer: show images from the selected source.
#         The timeline viewer: select a time range to filter the thumbnails.
#         The toolbar: propose acces to fotocop setings and help.
#         The status bar: display information and warning messages.
#
#     Args:
#         sourceManager: reference to the images' sources manager.
#         splash: reference to the splash screen to show the main view initialization
#             progress.
#         *args, **kwargs: Any other positional and keyword argument are passed to
#             the parent QMainWindow.
#
#     Attributes:
#         _sourceManager: reference to the images' sources manager.
#         _splash: reference to the splash screen to show the main view initialization
#             progress.
#         _status: reference to the Main window status bar.
#     """

    def __init__(self, *args, **kwargs) -> None:
    # def __init__(self, sourceManager: SourceManager, splash, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
#
#         splash.setProgress(10, "Create Gui objects...")
#
#         self._splash = splash

        resources = Config.dfacto_settings.resources

        # Initialize the app's views. Init order fixed to comply with the editors' dependencies.
        client_selector = QtWidgets.QWidget()
        client_editor = QtWidgets.QWidget()
        invoice_selector = QtWidgets.QWidget()
        invoice_editor = QtWidgets.QWidget()
        service_selector = QtWidgets.QWidget()
        service_editor = QtWidgets.QWidget()
#         fsModel = FileSystemModel()
#         fsDelegate = FileSystemDelegate()
#         fsFilter = FileSystemFilter()
#         fsFilter.setSourceModel(fsModel)
#         self._sourceManager = sourceManager
#         sourceSelector = SourceSelector(sourceManager, fsModel, fsFilter, fsDelegate)
#
#         # https://stackoverflow.com/questions/42673010/how-to-correctly-load-images-asynchronously-in-pyqt5
#         thumbnailViewer = ThumbnailViewer()
#
#         timelineViewer = TimelineViewer(parent=self)
#
#         self._downloader = Downloader()
#         renamePanel = RenamePanel(downloader=self._downloader, parent=self)
#         destinationPanel = DestinationPanel(
#             downloader=self._downloader,
#             fsModel=fsModel,
#             fsFilter=fsFilter,
#             fsDelegate=fsDelegate,
#             parent=self,
#         )
#
#         self._sourceManager.sourcesChanged.connect(sourceSelector.displaySources)
#
#         self._sourceManager.sourceSelected.connect(sourceSelector.displaySelectedSource)
#         self._sourceManager.sourceSelected.connect(self.displaySelectedSource)
#         self._sourceManager.sourceSelected.connect(thumbnailViewer.setSourceSelection)
#         self._sourceManager.sourceSelected.connect(timelineViewer.setTimeline)
#         self._sourceManager.sourceSelected.connect(self._downloader.setSourceSelection)
#
#         self._sourceManager.imagesBatchLoaded.connect(thumbnailViewer.addImages)
#         self._sourceManager.imagesBatchLoaded.connect(self._downloader.addImages)
#
#         self._sourceManager.thumbnailLoaded.connect(thumbnailViewer.updateImage)
#
#         self._sourceManager.imagesInfoChanged.connect(timelineViewer.updateTimeline)
#         self._sourceManager.imagesInfoChanged.connect(self._downloader.updateImagesInfo)
#         self._sourceManager.imagesInfoChanged.connect(self.updateDownloadButtonText)
#         self._sourceManager.imagesInfoChanged.connect(thumbnailViewer.updateToolbar)
#
#         self._sourceManager.timelineBuilt.connect(timelineViewer.finalizeTimeline)
#
#         self._sourceManager.imageSampleChanged.connect(self._downloader.updateImageSample)
#
#         self._downloader.imageNamingTemplateSelected.connect(
#             renamePanel.imageNamingTemplateSelected
#         )
#         self._downloader.imageNamingExtensionSelected.connect(
#             renamePanel.imageNamingExtensionSelected
#         )
#         self._downloader.destinationNamingTemplateSelected.connect(
#             destinationPanel.destinationNamingTemplateSelected
#         )
#
#         self._downloader.imageSampleChanged.connect(renamePanel.updateImageSample)
#         self._downloader.folderPreviewChanged.connect(
#             destinationPanel.folderPreviewChanged
#         )
#
#         self._downloader.destinationSelected.connect(
#             destinationPanel.destinationSelected
#         )
#
#         self._downloader.sessionRequired.connect(thumbnailViewer.requestSession)
#
#         thumbnailViewer.zoomLevelChanged.connect(timelineViewer.zoom)
#
#         timelineViewer.zoomed.connect(thumbnailViewer.onZoomLevelChanged)
#         timelineViewer.hoveredNodeChanged.connect(thumbnailViewer.showNodeInfo)
#         timelineViewer.timeRangeChanged.connect(thumbnailViewer.updateTimeRange)
#
#         splash.setProgress(30)

        # Build the main view layout.
        left_vert_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        left_vert_splitter.setChildrenCollapsible(False)
        left_vert_splitter.setHandleWidth(3)
        left_vert_splitter.addWidget(client_selector)
        left_vert_splitter.addWidget(client_editor)
        left_vert_splitter.setStretchFactor(0, 3)
        left_vert_splitter.setStretchFactor(1, 1)
        left_vert_splitter.setOpaqueResize(False)

        center_vert_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        center_vert_splitter.setChildrenCollapsible(False)
        center_vert_splitter.setHandleWidth(3)
        center_vert_splitter.addWidget(invoice_selector)
        center_vert_splitter.addWidget(invoice_editor)
        center_vert_splitter.setStretchFactor(0, 1)
        center_vert_splitter.setStretchFactor(1, 3)
        center_vert_splitter.setOpaqueResize(False)

        right_vert_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        right_vert_splitter.setChildrenCollapsible(False)
        right_vert_splitter.setHandleWidth(3)
        right_vert_splitter.addWidget(service_selector)
        right_vert_splitter.addWidget(service_editor)
        right_vert_splitter.setStretchFactor(0, 3)
        right_vert_splitter.setStretchFactor(1, 1)
        right_vert_splitter.setOpaqueResize(False)

        horz_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        horz_splitter.setChildrenCollapsible(False)
        horz_splitter.setHandleWidth(3)
        horz_splitter.addWidget(left_vert_splitter)
        horz_splitter.addWidget(center_vert_splitter)
        horz_splitter.addWidget(right_vert_splitter)
        horz_splitter.setStretchFactor(0, 1)
        horz_splitter.setStretchFactor(1, 3)
        horz_splitter.setStretchFactor(2, 1)
        horz_splitter.setOpaqueResize(False)

        self.setCentralWidget(horz_splitter)

        # Build actions used in toolbars.
#         self.downloadAction = QtUtil.createAction(
#             self,
#             "&Download",
#             slot=self.doDownloadAction,
#             tip="Download selected images",
#             shortcut="Ctrl+Return",
#             icon=f"{resources}/download.png",
#         )
        preferences_action = QtUtil.createAction(
            self,
            "Se&ttings",
            slot=self.do_preferences_action,
            shortcut="Ctrl+P",
            icon=f"{resources}/settings.png",
            tip="Adjust application settings",
        )
        about_action = QtUtil.createAction(
            self,
            "&About",
            slot=self.do_about_action,
            tip="About the application",
            shortcut="Ctrl+?",
            icon=f"{resources}/about.png",
        )
        quit_action = QtUtil.createAction(
            self,
            "&Quit",
            slot=self.close,
            tip="Close the application",
            shortcut="Ctrl+Q",
            icon=f"{resources}/close-window.png",
        )
#
#         self.downloadButton = DownloadButton(self.downloadAction.text())
#         self.downloadButton.setToolTip(self.downloadAction.toolTip())
#         self.downloadButton.setStatusTip(self.downloadAction.statusTip())
#         self.downloadButton.setDefault(True)
#         self.downloadButton.clicked.connect(self.downloadButtonClicked)
#         self._downloader.sessionRequired.connect(self.downloadButton.requestSession)
#         self._downloader.datetimeRequired.connect(self.downloadButton.requestDatetime)
#
#         sourceWidget = QtWidgets.QWidget()
#         self.sourcePix = QtWidgets.QLabel()
#         self.sourceLbl = QtWidgets.QLabel()
#         self.sourceLbl.setFrameShape(QtWidgets.QFrame.NoFrame)
#         self.sourceLbl.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
#         self.sourceLbl.setFixedWidth(350)
#         srcLayout = QtWidgets.QHBoxLayout()
#         srcLayout.setContentsMargins(10, 0, 10, 0)
#         srcLayout.addWidget(self.sourcePix, 0, QtCore.Qt.AlignCenter)
#         srcLayout.addWidget(self.sourceLbl, 0, QtCore.Qt.AlignCenter)
#         srcLayout.addStretch()
#         sourceWidget.setLayout(srcLayout)

        # To right-align the main toolbar.
        spacer = QtWidgets.QWidget(self)
        spacer.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred
        )

        # Build the main toolbar.
        self.menu = QtWidgets.QMenu()
        # self.menu.addAction(self.downloadAction)
        self.menu.addAction(preferences_action)
        self.menu.addSeparator()
        self.menu.addAction(about_action)
        self.menu.addAction(quit_action)

        self.menu_btn = QtWidgets.QToolButton()
        self.menu_btn.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        icon_size = QtCore.QSize(24, 24)
        menu_icon = QtGui.QIcon(f"{resources}/hamburger-menu.png")
        self.menu_btn.setIconSize(icon_size)
        self.menu_btn.setIcon(menu_icon)
        self.menu_btn.setMenu(self.menu)

        self.top_bar = self.addToolBar("Dfacto")
        self.top_bar.setIconSize(QtCore.QSize(36, 36))
        self.top_bar.installEventFilter(self)
        self.top_bar.setFloatable(False)
        self.top_bar.setMovable(False)
        self.top_bar.setStyleSheet("QPushButton{margin-right: 20 px;}")
        # self.top_bar.addWidget(sourceWidget)
        self.top_bar.addWidget(spacer)
        # self.top_bar.addWidget(self.downloadButton)
        self.top_bar.addWidget(self.menu_btn)
#
#         self.downloadProgress = DownloadProgress(self._downloader, self)
#         self._downloader.backgroundActionStarted.connect(self.downloadProgress.reinit)
#         self._downloader.backgroundActionProgressChanged.connect(
#             self.downloadProgress.updateProgress
#         )
#         self._downloader.backgroundActionCompleted.connect(
#             self.downloadProgress.terminate
#         )
#         self._downloader.backgroundActionCancelled.connect(
#             self.downloadProgress.onCancel
#         )

        # Build the status bar.
#         actionProgressBar = QtUtil.BackgroundProgressBar()
#         actionProgressBar.hide()
#         self._sourceManager.backgroundActionStarted.connect(
#             actionProgressBar.showActionProgress
#         )
#         self._sourceManager.backgroundActionProgressChanged.connect(
#             actionProgressBar.setActionProgressValue
#         )
#         self._sourceManager.backgroundActionCompleted.connect(
#             actionProgressBar.hideActionProgress
#         )
#         self._downloader.backgroundActionStarted.connect(
#             actionProgressBar.showActionProgress
#         )
#         self._downloader.backgroundActionProgressChanged.connect(
#             actionProgressBar.setActionProgressValue
#         )
#         self._downloader.backgroundActionCompleted.connect(
#             actionProgressBar.hideActionProgress
#         )
#         self._downloader.backgroundActionCancelled.connect(
#             actionProgressBar.hideActionProgress
#         )

        self._status = QtUtil.StatusBar()
        self.setStatusBar(self._status)
#         self._status.addPermanentWidget(actionProgressBar)
#
#         # Enumerate images sources
#         splash.setProgress(50, "Enumerating images sources...")
#         self._sourceManager.enumerateSources()

        # Finalize the main window initialization once it is built.
        QtCore.QTimer.singleShot(0, self.initUI)

    def initUI(self):
        """Intialize the main window to its last position.

        Called on an immediate timer once the main windows is built.
        """
        # self._splash.setProgress(70, "Load company settings")

        settings = Config.dfacto_settings

        self.move(settings.window_position[0], settings.window_position[1])
        self.resize(settings.window_size[0], settings.window_size[1])
        #
        # self._downloader.selectDestination(Path(settings.lastDestination))
        # self._downloader.setNamingTemplate(
        #     TemplateType.IMAGE, settings.lastImageNamingTemplate
        # )
        # self._downloader.setNamingTemplate(
        #     TemplateType.DESTINATION, settings.lastDestinationNamingTemplate
        # )
        # self._downloader.setExtension(Case[settings.lastNamingExtension])
        #
        # self._splash.setProgress(100)

    def show_status_message(self, msg: str, is_warning: bool = False, delay: int = None):
        """Convenient function to display a status message.

        Encapsulate the displayMessage method of the customized statusBar.

        Args:
            msg: the message string to display.
            is_warning: True when the message is a warning
                (displayed in WARNING_MSG_STYLE for a longer default time).
            delay: the time to keep the message displayed
                (default is 5s for an information and 2s for a warning).
        """
        self._status.displayMessage(msg, is_warning, delay)
#
#     def okToContinue(self) -> bool:
#         """Authorize app exit, project creation or loading.
#
#         Ask for confirmation if the project is valid and has pending changes.
#
#         Returns:
#             True if action is authorized, False otherwise.
#         """
#         # if self.project and self.project.isValid and self.project.isDirty:
#         #     reply = QtWidgets.QMessageBox.question(
#         #         self,  # noqa
#         #         f"{QtWidgets.qApp.applicationName()} - Unsaved Changes",
#         #         "Save project changes?",
#         #         (
#         #             QtWidgets.QMessageBox.Yes
#         #             | QtWidgets.QMessageBox.No
#         #             | QtWidgets.QMessageBox.Cancel
#         #         ),
#         #     )  # noqa
#         #     if reply == QtWidgets.QMessageBox.Cancel:
#         #         return False
#         #     elif reply == QtWidgets.QMessageBox.Yes:
#         #         return self.saveProject()
#         return True
#
#     @QtCore.pyqtSlot(Source)
#     def displaySelectedSource(self, source: "Source") -> None:
#         """Update the sourceSelector widgets on source selection.
#
#         Call when the source manager signals that a source is selected. The selected
#         source may be a Device or a LogicalDisk object, or unknown (none).
#
#         Args:
#             source: the selected source of the source manager.
#         """
#         resources = Config.fotocopSettings.resources
#
#         media = source.media
#
#         if source.isDevice:
#             caption = media.caption
#             self.sourcePix.setPixmap(
#                 QtGui.QPixmap(f"{resources}/device.png").scaledToHeight(
#                     48, QtCore.Qt.SmoothTransformation
#                 )
#             )
#             QtUtil.setElidedText(self.sourceLbl, f"FROM {caption}\nAll pictures")
#             toolTip = f"Device: {caption}"
#             self.sourceLbl.setToolTip(toolTip)
#             self.sourceLbl.setStatusTip(toolTip)
#
#         elif source.isLogicalDisk:
#             icon = SourceSelector.DRIVE_ICON.get(media.driveType, "drive.png")
#             self.sourcePix.setPixmap(
#                 QtGui.QPixmap(f"{resources}/{icon}").scaledToHeight(
#                     48, QtCore.Qt.SmoothTransformation
#                 )
#             )
#             caption = media.caption
#             path = source.selectedPath
#             posixPath = path.as_posix()
#             sourcePath = posixPath[3:].replace("/", " / ")
#             subDirs = source.subDirs
#             QtUtil.setElidedText(
#                 self.sourceLbl, f"FROM {caption}\n{sourcePath}{' +' if subDirs else ''}"
#             )
#             toolTip = f"Drive: {caption}\nPath: {posixPath}{' (including subfolders)' if subDirs else ''}"
#             self.sourceLbl.setToolTip(toolTip)
#             self.sourceLbl.setStatusTip(toolTip)
#
#         else:
#             assert source.isEmpty
#             self.sourcePix.setPixmap(
#                 QtGui.QPixmap(f"{resources}/double-down.png").scaledToHeight(
#                     48, QtCore.Qt.SmoothTransformation
#                 )
#             )
#             self.sourceLbl.setText("Select a source")
#             self.sourceLbl.setToolTip("")
#             self.sourceLbl.setStatusTip("")
#
#         self.updateDownloadButtonText([], ImageProperty.IS_SELECTED, True)
#
#     @QtCore.pyqtSlot()
#     def doDownloadAction(self):
#         self.downloadButton.animateClick()

    @QtCore.pyqtSlot()
    def do_preferences_action(self):
        # TODO: Create a settings dialog.
        """Show the Dfacto settings dialog.

        If dialog is accepted, the settings changes are saved.
        """
        self.show_status_message("Preferences...")
        # form = SettingsView(parent=self)
        # if form.exec_():
        #     Config.dfacto_settings.save()

    @QtCore.pyqtSlot()
    def do_about_action(self):
        """Show the Fotocop 'About' dialog."""
        pass
        resources = Config.dfacto_settings.resources
        app_name = __about__.__title__
        QtWidgets.QMessageBox.about(
            self,  # noqa
            f"{app_name} - About",
            f"""
            <p><b>{app_name}</b> {__about__.__version__}</p>
            <p>{__about__.__summary__}.</p>
            <br>
            <p>
            Designed and develop by {__about__.__author__}
            ({__about__.__email__})
            </p>
            <p>
            Under {__about__.__license__} license - {__about__.__copyright__}
            </p>
            <br>
            <p>
            Powered by
            <a href="https://www.python.org/">
            <img style="vertical-align:middle" src="{resources}/pythonlogo.svg" alt="Powered by Python" height="32"></a>
             and
            <a href="https://www.qt.io/">
            <img style="vertical-align:middle" src="{resources}/qtlogo.svg" alt="Powered by Qt" height="32"></a>
            </p>
            <p>
            Icons selection from icons8.com <a href="https://icons8.com">
            <img style="vertical-align:middle" src="{resources}/icons8.png" alt="icons8.com" height="32"></a>
            </p>
            """,
        )
#
#     @QtCore.pyqtSlot()
#     def downloadButtonClicked(self) -> None:
#         if self.downloadButton.sessionRequired:
#             sourceSelection = self._sourceManager.source
#             imageKeys = sourceSelection.getImagesRequiringSession()
#             if imageKeys:
#                 dialog = SessionEditor(imagesCount=len(imageKeys), parent=self)
#                 if dialog.exec():
#                     session = dialog.session
#                 else:
#                     session = ""
#                 if not session:
#                     return
#                 sourceSelection.setImagesSession(imageKeys, session)
#
#         self._downloader.download()
#
#     @QtCore.pyqtSlot(list, Enum, object)
#     def updateDownloadButtonText(
#             self,
#             _imageKeys: List["ImageKey"],
#             pty: "ImageProperty",
#             _value
#     ) -> None:
#         source = self._sourceManager.source
#         timelineBuilt = source.timelineBuilt
#         if pty is ImageProperty.IS_SELECTED or (pty is ImageProperty.DATETIME and timelineBuilt):
#             count = source.selectedImagesCount
#             text = f" {count} images" if count > 1 else f" 1 image" if count == 1 else ""
#             self.downloadButton.setText(f"Download{text}")
#             selOk = count > 0
#             dateOk = (
#                 not self.downloadButton.datetimeRequired
#                 or timelineBuilt
#             )
#             self.downloadButton.setEnabled(selOk and dateOk)

    def keyPressEvent(self, e: QtGui.QKeyEvent):
        """Trap the Escape key to close the application.

        Reimplement the parent QMainWindow event handler to trap the Escape key
        pressed event. Other key pressed event are passed to the parent.

        Args:
            e: keyboard's key pressed event
        """
        if e.key() == QtCore.Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(e)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Trap the main window close request to allow saving pending changes.

        Save the downloader sequences and the application settings.

        Args:
            event: the window close request
        """
        # self._downloader.saveSequences()

        Config.dfacto_settings.window_position = (
            self.frameGeometry().x(),
            self.frameGeometry().y(),
        )
        Config.dfacto_settings.window_size = (
            self.geometry().width(),
            self.geometry().height(),
        )
        try:
            Config.dfacto_settings.save()
        except Config.settings.SettingsError as e:
            reply = QtWidgets.QMessageBox.question(
                self,  # noqa
                f"{QtWidgets.QApplication.applicationName()} - Exit confirmation",
                f"Cannot save the settings file ({e}): quit anyway?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            )
            if reply == QtWidgets.QMessageBox.StandardButton.No:
                # reject dialog close event
                event.ignore()
                return

        # Saving dfacto_settings OK or reply == QMessageBox.Yes
        # self._sourceManager.close()
        # self._downloader.close()

    def eventFilter(self, obj, event) -> bool:
        # https://www.qtcentre.org/threads/7718-How-to-disable-context-menu-of-a-toolbar-in-QMainApplication
        if event.type() == QtCore.QEvent.Type.ContextMenu and obj == self.top_bar:
            return True

        return super().eventFilter(obj, event)


def qt_main() -> None:
    """Main Graphical Interface entry point.

    Retrieves settings, initiatizes the whole application logging. Then initializes
    a Qt Application and the application main view.
    Display a splash screen during application initialization and start the Qt main loop.
    """
    # https://stackoverflow.com/questions/67599432/setting-the-same-icon-as-application-icon-in-task-bar-for-pyqt5-application
    # import ctypes
    # myappid = 'fotocop'  # arbitrary string
    # ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    # or create HKEY_LOCAL_MACHINE\SOFTWARE\Classes\Applications\python.exe with an empty
    # IsHostApp chain value

    # Retrieve the fotocop app settings.
    settings = Config.dfacto_settings
    resources = settings.resources
    templates = settings.templates

    # Initialize and start the log server.
    log_config = LogConfig(
        settings.app_dirs.user_log_dir / "dfacto.log",
        settings.log_level,
        log_on_console=True,
    )
    log_config.init_logging()

    logger.info("Dfacto is starting...")

    # QT_SCALE_FACTOR environment variable allow to zoom the HMI for better.
    # readability
    if "QT_SCALE_FACTOR" not in os.environ:
        os.environ["QT_SCALE_FACTOR"] = settings.qt_scale_factor

    # Initialize the Application, apply a custom style, set the app's icon and
    # increase the default font size.
    app = QtWidgets.QApplication(sys.argv)
    # app.setStyle(QtUtil.MyAppStyle())
    app.setStyleSheet("QSplitter::handle { background-color: gray }")
    app.setApplicationName("Dfacto")
    # app.setAttribute(QtCore.Qt.AA_DisableWindowContextHelpButton)
    app.setWindowIcon(QtGui.QIcon(f"{resources}/fotocop.svg"))
    f = app.font()
    fSize = f.pointSize()
    f.setPointSize(fSize + 2)
    app.setFont(f)

    # Select a company profile
    logger.info("Selecting a company profile...")
    company_profile = _select_company_profile()
    if company_profile is None:
        logger.info(f"No company profile is selected: Dfacto is closing...")
        # Stop the log server.
        log_config.stop_logging()
        return
    Config.dfacto_settings.last_profile = company_profile.name
    logger.info(f"Company profile {company_profile.name} is selected")

    # Connect to the database of the selected company
    logger.info("Connecting to database...")
    db_path = company_profile.home / "dfacto.db"
    engine = db.configure_session(db.Session, db_path)
    db.init_db(engine, db.Session)
    logger.info(f"Connected to {db_path}")

    # Initialize the images sources manager.
    # sourceManager = SourceManager()

    # Build and show the splash screen.
    # splash = QtUtil.SplashScreen(
    #     f"{resources}/splashscreen600.png",
    #     __about__.__version__,
    #     QtCore.Qt.WindowStaysOnTopHint,
    # )
    # splash.show()

    # Build and show the main view after the splash screen delay.
    mainView = QtMainView()
    # splash.finish(mainView)
    mainView.show()

    # Start the Qt main loop.
    app.exec()

    # Config.dfacto_settings.save()
    logger.info("Dfacto is closing...")
    # Stop the log server.
    log_config.stop_logging()


def _select_company_profile() -> Optional[schemas.Company]:
    # If a previously used company profile exists, select it.
    last_profile = Config.dfacto_settings.last_profile
    response = api.company.get(last_profile)
    if response.status is CommandStatus.COMPLETED:
        return response.body

    # If some company profiles already exists, ask to select one of them.
    companies = api.company.get_all().body
    add = False
    if len(companies) > 0:
        # Open the company selection dialog to select a company among the existing ones,
        a_dialog = SelectCompanyDialog(profiles=companies, fixed_size=True)
        if a_dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        company = a_dialog.company
        if company is not None:
            return company
        # No company is selected but the user requests to add a new one
        add = True

    # Open company creation dialog to create a new company and select it
    if add:
        # Some companies exist, create a new one
        mode = AddCompanyDialog.Mode.ADD
    else:
        # No company exists, create the first new one
        mode = AddCompanyDialog.Mode.NEW
    names_in_use = [company.name for company in companies]
    a_dialog = AddCompanyDialog(forbidden_names=names_in_use, fixed_size=True)
    a_dialog.reset()
    a_dialog.set_mode(mode)
    if a_dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        return
    company = a_dialog.company
    # Add the new company profile to the database (the Dfacto settings JSON file)
    response = api.company.add(company)
    if response.status is not CommandStatus.COMPLETED:
        logger.warning(
            "Cannot create the %s company profile - Reason is: %s",
            company.name, response.reason
        )
        QtWidgets.QMessageBox.warning(
            None,  # type: ignore
            f"Dfacto - Connection failed",
            f"Cannot create the {company.name} company profile\n\nReason is:\n{response.reason}",
            QtWidgets.QMessageBox.StandardButton.Close,
        )
        return
    return response.body


if __name__ == "__main__":
    qt_main()