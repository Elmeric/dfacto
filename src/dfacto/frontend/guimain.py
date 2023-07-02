# Copyright (c) 2023, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Entry point of the Dfacto application.
"""
import logging
import os
import sys
import time
from decimal import Decimal
from typing import Any, Optional

import PyQt6.QtCore as QtCore
import PyQt6.QtGui as QtGui
import PyQt6.QtWidgets as QtWidgets
from babel.numbers import format_currency

import dfacto.__about__ as __about__

# Models
from dfacto import settings as Config
from dfacto.backend import api, schemas
from dfacto.backend.api.command import CommandStatus

# Util
from dfacto.util import qtutil as QtUtil
from dfacto.util.settings import SettingsError

# Views
from .basketviewer import BasketTableModel, BasketViewer
from .clientselector import ClientSelector
from .companydialogs import AddCompanyDialog, SelectCompanyDialog
from .invoiceviewer import InvoiceTableModel, InvoiceViewer
from .serviceselector import ServiceSelector

__all__ = ["qt_main"]

logger = logging.getLogger(__name__)


class QtMainView(QtWidgets.QMainWindow):
    """The Dfacto main view.

    The Main view is composed of:
        The client selector:  Create, edit delete clients and select one.
        The service selector:  Create, edit delete services and add them
            to the basket of the selected client.
        The basket viewer: Show and edit the basket of the selected client.
        The invoices viewer: a filterable list invoices where all invoices
            actions are available.
        The toolbar: Show a summary of pending payments and sales as well
            as a company profile selector
        The toolbar menu: propose access to fotocop settings and help.
        The status bar: display information and warning messages.

    Args:
        company_profile: reference to the selected company profile.
        splash: reference to the splash screen to show the main view initialization
            progress.
        *args, **kwargs: Any other positional and keyword argument are passed to
            the parent QMainWindow.

    Attributes:
        company_profile: reference to the selected company profile.
    """

    def __init__(
        self,
        company_profile: schemas.Company,
        splash: QtUtil.SplashScreen,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.company_profile = company_profile
        super().__init__(*args, **kwargs)

        splash.setProgress(10, _("Create Gui objects..."))
        time.sleep(1)

        self._splash = splash

        resources = Config.dfacto_settings.resources

        self._pending_payments: schemas.Amount = schemas.Amount()
        self._last_quarter_sales: schemas.Amount = schemas.Amount()
        self._current_quarter_sales: schemas.Amount = schemas.Amount()

        # Initialize the app's views. Init order fixed to comply with the editors' dependencies.
        self.client_selector = ClientSelector()
        basket_model = BasketTableModel()
        self.basket_viewer = BasketViewer(basket_model)
        invoice_model = InvoiceTableModel()
        self.invoice_viewer = InvoiceViewer(invoice_model)
        self.service_selector = ServiceSelector(basket_model)
        self.pending_payments_lbl = QtWidgets.QLabel()
        self.pending_payments_lbl.setMargin(5)
        self.pending_payments_lbl.setFrameStyle(
            QtWidgets.QFrame.Shape.StyledPanel | QtWidgets.QFrame.Shadow.Raised
        )
        self.pending_payments_lbl.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self.sales_summary_lbl = QtWidgets.QLabel()
        self.sales_summary_lbl.setMargin(5)
        self.sales_summary_lbl.setFrameStyle(
            QtWidgets.QFrame.Shape.StyledPanel | QtWidgets.QFrame.Shadow.Raised
        )
        self.sales_summary_lbl.setWordWrap(True)
        self.sales_summary_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.client_selector.client_selected.connect(
            self.basket_viewer.set_current_client
        )
        self.client_selector.client_selected.connect(
            self.invoice_viewer.set_current_client
        )
        self.basket_viewer.selection_changed.connect(
            self.service_selector.select_service_by_name
        )
        self.basket_viewer.invoice_created.connect(
            self.invoice_viewer.on_invoice_creation
        )
        self.invoice_viewer.basket_updated.connect(self.basket_viewer.on_basket_update)
        invoice_model.pending_payment_created.connect(self.do_set_pending_pmt)
        invoice_model.pending_payment_changed.connect(self.do_update_pending_pmt)
        invoice_model.sales_summary_created.connect(self.do_set_sales_summary)
        invoice_model.sales_summary_changed.connect(self.do_update_sales_summary)

        splash.setProgress(30)

        # Build the main view layout.
        left_vert_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        left_vert_splitter.setContentsMargins(0, 0, 5, 5)
        left_vert_splitter.setChildrenCollapsible(False)
        left_vert_splitter.setHandleWidth(3)
        left_vert_splitter.addWidget(self.client_selector)
        left_vert_splitter.setStretchFactor(0, 3)
        left_vert_splitter.setStretchFactor(1, 1)
        left_vert_splitter.setOpaqueResize(False)

        center_vert_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        center_vert_splitter.setContentsMargins(5, 0, 5, 5)
        center_vert_splitter.setChildrenCollapsible(False)
        center_vert_splitter.setHandleWidth(3)
        center_vert_splitter.addWidget(self.invoice_viewer)
        center_vert_splitter.addWidget(self.basket_viewer)
        center_vert_splitter.setStretchFactor(0, 4)
        center_vert_splitter.setStretchFactor(1, 3)
        center_vert_splitter.setOpaqueResize(False)

        right_vert_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        right_vert_splitter.setContentsMargins(5, 0, 0, 5)
        right_vert_splitter.setChildrenCollapsible(False)
        right_vert_splitter.setHandleWidth(3)
        right_vert_splitter.addWidget(self.service_selector)
        right_vert_splitter.setStretchFactor(0, 3)
        right_vert_splitter.setStretchFactor(1, 1)
        right_vert_splitter.setOpaqueResize(False)

        horz_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        horz_splitter.setContentsMargins(0, 0, 0, 0)
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
        edit_profile_action = QtUtil.createAction(
            self,
            _("Edit your company profile"),
            slot=self.do_edit_profile_action,
            tip=_("Edit your company profile"),
            shortcut="Ctrl+E",
            icon=f"{resources}/edit.png",
        )
        select_profile_action = QtUtil.createAction(
            self,
            _("Select another company profile"),
            slot=self.do_select_profile_action,
            tip=_("Select another company profile"),
            shortcut="Alt+P",
            icon=f"{resources}/change.png",
        )
        new_profile_action = QtUtil.createAction(
            self,
            _("New company profile"),
            slot=self.do_new_profile_action,
            tip=_("Create a new company profile"),
            shortcut="Ctrl+N",
            icon=f"{resources}/add.png",
        )
        preferences_action = QtUtil.createAction(
            self,
            _("Settings"),
            slot=self.do_preferences_action,
            tip=_("Adjust application settings"),
            shortcut="Ctrl+P",
            icon=f"{resources}/settings.png",
        )
        about_action = QtUtil.createAction(
            self,
            _("About %s") % __about__.__title__,
            slot=self.do_about_action,
            tip=_("About %s") % __about__.__title__,
            shortcut="Ctrl+?",
            icon=f"{resources}/about.png",
        )
        quit_action = QtUtil.createAction(
            self,
            _("Quit"),
            slot=self.close,
            tip=_("Close the application"),
            shortcut="Ctrl+Q",
            icon=f"{resources}/close-window.png",
        )

        # To right-align the main toolbar.
        spacer = QtWidgets.QWidget(self)
        spacer.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )

        # Build the main toolbar.
        self.company_menu = QtWidgets.QMenu()
        self.company_menu.addAction(edit_profile_action)
        self.company_menu.addSeparator()
        self.company_menu.addAction(select_profile_action)
        self.company_menu.addAction(new_profile_action)

        self.company_btn = QtWidgets.QToolButton()
        self.company_btn.setPopupMode(
            QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup
        )
        self.company_btn.setToolButtonStyle(
            QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        icon_size = QtCore.QSize(24, 24)
        menu_icon = QtGui.QIcon(f"{resources}/company.png")
        self.company_btn.setIconSize(icon_size)
        self.company_btn.setIcon(menu_icon)
        self.company_btn.setText(company_profile.name)
        self.company_btn.setMenu(self.company_menu)

        self.menu = QtWidgets.QMenu()
        self.menu.addAction(preferences_action)
        self.menu.addSeparator()
        self.menu.addAction(about_action)
        self.menu.addAction(quit_action)

        self.menu_btn = QtWidgets.QToolButton()
        self.menu_btn.setPopupMode(
            QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup
        )
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
        self.top_bar.setStyleSheet("QLabel{margin-right: 20 px;}")
        self.top_bar.addWidget(self.pending_payments_lbl)
        self.top_bar.addWidget(self.sales_summary_lbl)
        self.top_bar.addWidget(spacer)
        self.top_bar.addWidget(self.company_btn)
        self.top_bar.addWidget(self.menu_btn)

        # Build the status bar.
        self._status = QtUtil.StatusBar()
        self.setStatusBar(self._status)

        # Enumerate images sources
        splash.setProgress(50)

        # Finalize the main window initialization once it is built.
        QtCore.QTimer.singleShot(0, self.initUI)

    def initUI(self) -> None:
        """Intialize the main window to its last position.

        Called on an immediate timer once the main windows is built.
        """
        self._splash.setProgress(70, _("Loading database..."))
        time.sleep(1)

        settings = Config.dfacto_settings

        self.move(settings.window_position[0], settings.window_position[1])
        self.resize(settings.window_size[0], settings.window_size[1])

        self.service_selector.load_services()
        self.invoice_viewer.load_invoices()
        self.client_selector.load_clients()

        self._splash.setProgress(100)

    def show_status_message(
        self,
        msg: str,
        is_warning: bool = False,
        delay: Optional[int] = None,
    ) -> None:
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

    @QtCore.pyqtSlot()
    def do_edit_profile_action(self) -> None:
        # Retrieve the current company profile
        response = api.company.get_current()
        if response.status is not CommandStatus.COMPLETED:
            logger.warning(
                _("Cannot edit your company profile - Reason is: %s"), response.reason
            )
            QtWidgets.QMessageBox.warning(
                None,  # type: ignore
                _("Dfacto - Connection failed"),
                _("Cannot edit your company profile\n\nReason is:\n%s")
                % response.reason,
                QtWidgets.QMessageBox.StandardButton.Close,
            )
            return
        current_profile = response.body

        # Open the Add-Edit Company Dialog in EDIT mode and load the current profile
        a_dialog = AddCompanyDialog(fixed_size=True)
        a_dialog.reset()
        a_dialog.set_mode(AddCompanyDialog.Mode.EDIT)
        a_dialog.edit_profile(current_profile)

        if a_dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        company = a_dialog.updated_company

        # Update the company profile in the database (the Dfacto settings JSON file)
        response = api.company.update(current_profile.name, obj_in=company)
        if response.status is not CommandStatus.COMPLETED:
            logger.warning(
                _("Cannot update the %s company profile - Reason is: %s"),
                current_profile.name,
                response.reason,
            )
            QtWidgets.QMessageBox.warning(
                None,  # type: ignore
                _("Dfacto - Connection failed"),
                _("Cannot update the %s company profile\n\nReason is:\n%s")
                % (current_profile.name, response.reason),
                QtWidgets.QMessageBox.StandardButton.Close,
            )
            return

        self.company_btn.setText(response.body.name)

    @QtCore.pyqtSlot()
    def do_select_profile_action(self) -> None:
        companies = api.company.get_others().body

        if len(companies) <= 0:
            QtWidgets.QMessageBox.information(
                None,  # type: ignore
                _("Dfacto - Company profile selection"),
                _(
                    "No other company profiles available: use 'New company profile' to create one"
                ),
                QtWidgets.QMessageBox.StandardButton.Close,
            )
            return

        a_dialog = SelectCompanyDialog(profiles=companies, fixed_size=True)

        if a_dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        company = a_dialog.company

        if company is None:
            # The user request to create a new company profile
            self.do_new_profile_action()
        else:
            # Select the requested company profile
            self._select_profile(company, is_new=False)

    @QtCore.pyqtSlot()
    def do_new_profile_action(self) -> None:
        a_dialog = AddCompanyDialog(fixed_size=True)
        a_dialog.reset()
        a_dialog.set_mode(AddCompanyDialog.Mode.ADD)

        if a_dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        company = a_dialog.company

        # Add the new company profile to the database (the Dfacto settings JSON file)
        response = api.company.add(company)
        if response.status is not CommandStatus.COMPLETED:
            logger.warning(
                _("Cannot create the %s company profile - Reason is: %s"),
                company.name,
                response.reason,
            )
            QtWidgets.QMessageBox.warning(
                None,  # type: ignore
                _("Dfacto - Connection failed"),
                _("Cannot create the %s company profile\n\nReason is:\n%s")
                % (company.name, response.reason),
                QtWidgets.QMessageBox.StandardButton.Close,
            )
            return

        # Select the new company profile
        self._select_profile(response.body, is_new=True)

    def _select_profile(self, company: schemas.Company, is_new: bool) -> None:
        logger.info(_("Selecting the company profile..."))
        logger.info(_("Connecting to database..."))

        response = api.company.select(company.name, is_new=is_new)

        if response.status is not CommandStatus.COMPLETED:
            QtUtil.raise_fatal_error(
                _("Cannot select the %s company profile\n\nReason is:\n%s")
                % (company.name, response.reason)
            )

        self.company_btn.setText(company.name)

        # Reload objects from the new company profile to update UI
        # Basket is reloaded when on automatic client selection after client loading
        self.service_selector.load_services()
        self.invoice_viewer.load_invoices()
        self.client_selector.load_clients()

        logger.info(_("Connected to %s"), company.home / "dfacto.db")
        logger.info(_("Company profile %s is selected"), company.name)

    @QtCore.pyqtSlot(schemas.Amount)
    def do_set_pending_pmt(self, pmt: schemas.Amount) -> None:
        nbsp = "\u00A0"
        self._pending_payments = pmt
        if pmt == Decimal(0):
            self.pending_payments_lbl.setText(
                _("No pending payments").replace(" ", nbsp)
            )
            return
        pending_str = format_currency(
            pmt.net, "EUR", locale=Config.dfacto_settings.locale
        ).replace(" ", nbsp)
        self.pending_payments_lbl.setText(
            (_("Pending payments: <strong>%s</strong>") % pending_str).replace(
                " ", nbsp
            )
        )

    @QtCore.pyqtSlot(schemas.Amount)
    def do_update_pending_pmt(self, pmt: schemas.Amount) -> None:
        nbsp = "\u00A0"
        self._pending_payments += pmt
        new = self._pending_payments
        if new == Decimal(0):
            self.pending_payments_lbl.setText(
                _("No pending payments").replace(" ", nbsp)
            )
            return
        pending_str = format_currency(
            new.net, "EUR", locale=Config.dfacto_settings.locale
        ).replace(" ", nbsp)
        self.pending_payments_lbl.setText(
            (_("Pending payments: <strong>%s</strong>") % pending_str).replace(
                " ", nbsp
            )
        )

    @QtCore.pyqtSlot(schemas.Amount, schemas.Amount)
    def do_set_sales_summary(
        self, last: schemas.Amount, current: schemas.Amount
    ) -> None:
        nbsp = "\u00A0"
        self._last_quarter_sales = last
        self._current_quarter_sales = current
        locale_ = Config.dfacto_settings.locale
        last_str = format_currency(last.net, "EUR", locale=locale_)
        current_str = format_currency(current.net, "EUR", locale=locale_)
        lbl1 = _("Last quarter sales: ").replace(" ", nbsp)
        lbl2 = _("Current quarter sales: ").replace(" ", nbsp)
        summary = lbl1 + "<strong>%s</strong>\n" % last_str
        summary += lbl2 + "<strong>%s</strong>" % current_str
        self.sales_summary_lbl.setText(summary)

    @QtCore.pyqtSlot(schemas.Amount, schemas.Amount)
    def do_update_sales_summary(
        self, last: schemas.Amount, current: schemas.Amount
    ) -> None:
        nbsp = "\u00A0"
        self._last_quarter_sales += last
        self._current_quarter_sales += current
        locale_ = Config.dfacto_settings.locale
        last_str = format_currency(self._last_quarter_sales.net, "EUR", locale=locale_)
        current_str = format_currency(
            self._current_quarter_sales.net, "EUR", locale=locale_
        )
        lbl1 = _("Last quarter sales: ").replace(" ", nbsp)
        lbl2 = _("Current quarter sales: ").replace(" ", nbsp)
        summary = lbl1 + "<strong>%s</strong>\n" % last_str
        summary += lbl2 + "<strong>%s</strong>" % current_str
        self.sales_summary_lbl.setText(summary)

    @QtCore.pyqtSlot()
    def do_preferences_action(self) -> None:
        # TODO: Create a settings dialog.
        """Show the Dfacto settings dialog.

        If dialog is accepted, the settings changes are saved.
        """
        self.show_status_message(_("Preferences..."))
        # form = SettingsView(parent=self)
        # if form.exec_():
        #     Config.dfacto_settings.save()

    @QtCore.pyqtSlot()
    def do_about_action(self) -> None:
        """Show the Fotocop 'About' dialog."""
        pass
        resources = Config.dfacto_settings.resources
        app_name = __about__.__title__
        designed = _("Designed and develop by")
        license_ = _("Under %(license)s license") % {"license": __about__.__license__}
        powered_by = _("Powered by")
        and_ = _("and")
        icons = _("Icons selection from")
        QtWidgets.QMessageBox.about(
            self,  # noqa
            _("%(app_name)s - About") % {"app_name": app_name},
            f"""
            <p><b>{app_name}</b> {__about__.__version__}</p>
            <p>{__about__.__summary__}.</p>
            <br>
            <p>
            {designed} {__about__.__author__}
            ({__about__.__email__})
            </p>
            <p>
            {license_} - {__about__.__copyright__}
            </p>
            <br>
            <p>
            {powered_by}
            <a href="https://www.python.org/">
            <img style="vertical-align:middle" src="{resources}/pythonlogo.svg" alt="Powered by Python" height="32"></a>
             {and_}
            <a href="https://www.qt.io/">
            <img style="vertical-align:middle" src="{resources}/qtlogo.svg" alt="Powered by Qt" height="32"></a>
            </p>
            <p>
            {icons} icons8.com <a href="https://icons8.com">
            <img style="vertical-align:middle" src="{resources}/icons8.png" alt="icons8.com" height="32"></a>
            </p>
            """,
        )

    def keyPressEvent(self, e: QtGui.QKeyEvent) -> None:
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
        except SettingsError as e:
            app_name = __about__.__title__
            reply = QtWidgets.QMessageBox.question(
                self,  # noqa
                _("%(app_name)s - Exit confirmation") % {"app_name": app_name},
                _("Cannot save the settings file (%s): quit anyway?") % e,
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.No,
            )
            if reply == QtWidgets.QMessageBox.StandardButton.No:
                # reject dialog close event
                event.ignore()
                return

        # Saving dfacto_settings OK or reply == QMessageBox.Yes
        # self._sourceManager.close()
        # self._downloader.close()

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        # https://www.qtcentre.org/threads/7718-How-to-disable-context-menu-of-a-toolbar-in-QMainApplication
        if event.type() == QtCore.QEvent.Type.ContextMenu and obj == self.top_bar:
            return True

        return super().eventFilter(obj, event)


def qt_main() -> int:
    """Main Graphical Interface entry point.

    Retrieves settings, initiatizes the whole application logging. Then initializes
    a Qt Application and the application main view.
    Display a splash screen during application initialization and start the Qt main loop.
    """

    # Retrieve the fotocop app settings.
    settings = Config.dfacto_settings
    resources = settings.resources

    # QT_SCALE_FACTOR environment variable allow to zoom the HMI for better.
    # readability
    if "QT_SCALE_FACTOR" not in os.environ:
        os.environ["QT_SCALE_FACTOR"] = settings.qt_scale_factor

    # Initialize the Application, apply a custom style, set the app's icon and
    # increase the default font size.
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle(QtUtil.MyAppStyle())
    app.setStyleSheet("QSplitter::handle { background-color: gray }")
    app.setApplicationName(__about__.__title__)
    app.setWindowIcon(QtGui.QIcon(f"{resources}/invoice-32.ico"))
    f = app.font()
    fSize = f.pointSize()
    f.setPointSize(fSize + settings.font_size)
    app.setFont(f)

    # Select a company profile
    logger.info(_("Selecting a company profile..."))
    company_profile, is_new = _select_company_profile()
    if company_profile is None:
        logger.info(_("No company profile is selected: Dfacto is closing..."))
        return 1

    logger.info(_("Connecting to database..."))
    response = api.company.select(company_profile.name, is_new=is_new)
    if response.status is not CommandStatus.COMPLETED:
        logger.warning(
            _("Cannot select the %s company profile - Reason is: %s"),
            company_profile.name,
            response.reason,
        )
        QtWidgets.QMessageBox.warning(
            None,  # type: ignore
            _("Dfacto - Connection failed"),
            _("Cannot create the %(profile)s company profile\n\nReason is:\n%(reason)s")
            % {"profile": company_profile.name, "reason": response.reason},
            QtWidgets.QMessageBox.StandardButton.Close,
        )
        return 1
    logger.info(
        _("Connected to %(database)s"), {"database": company_profile.home / "dfacto.db"}
    )
    logger.info(
        _("Company profile %(profile)s is selected"), {"profile": company_profile.name}
    )

    # Build and show the splash screen.
    splash = QtUtil.SplashScreen(
        f"{resources}/splash.png",
        __about__.__version__,
        QtCore.Qt.WindowType.WindowStaysOnTopHint,
    )
    splash.show()

    # Build and show the main view after the splash screen delay.
    mainView = QtMainView(company_profile, splash)
    splash.finish(mainView)
    mainView.show()

    # Start the Qt main loop.
    app.exec()

    return 0


def _select_company_profile() -> tuple[Optional[schemas.Company], bool]:
    # If a previously used company profile exists, select it.
    response = api.company.get_current()
    if response.status is CommandStatus.COMPLETED:
        return response.body, False

    # If some company profiles already exists, ask to select one of them.
    companies = api.company.get_all().body
    add = False
    if len(companies) > 0:
        # Open the company selection dialog to select a company among the existing ones,
        a_dialog = SelectCompanyDialog(profiles=companies, fixed_size=True)
        if a_dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return None, False
        company = a_dialog.company
        if company is not None:
            return company, False
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

    dialog = AddCompanyDialog(forbidden_names=names_in_use, fixed_size=True)
    dialog.reset()
    dialog.set_mode(mode)

    if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        return None, False
    new_company = dialog.company

    # Add the new company profile to the database (the Dfacto settings JSON file)
    response = api.company.add(new_company)
    if response.status is not CommandStatus.COMPLETED:
        logger.warning(
            _("Cannot create the %(profile)s company profile - Reason is: %(reason)s"),
            {"profile": new_company.name, "reason": response.reason},
        )
        QtWidgets.QMessageBox.warning(
            None,  # type: ignore
            _("Dfacto - Connection failed"),
            _("Cannot create the %(profile)s company profile\n\nReason is:\n%(reason)s")
            % {"profile": new_company.name, "reason": response.reason},
            QtWidgets.QMessageBox.StandardButton.Close,
        )
        return None, False

    return response.body, True


if __name__ == "__main__":
    qt_main()
