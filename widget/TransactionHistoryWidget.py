import re

import pandas as pd
from PySide6 import QtCore, QtWidgets
from pytz import timezone

from data.OrderHistoryPandasModel import OrderHistoryPandasModel
from util.Thread import Worker
from widget import CalenderWidget, OrderHistoryTableView
from widget.WaitingSpinner import WaitingSpinner


class TransactionHistoryWidget(QtWidgets.QWidget):
    @property
    def from_date(self):
        return self.__from_date

    @from_date.setter
    def from_date(self, value):
        self.__from_date = value
        if self.order_history_df is not None:
            df_for_model = self.filtering_df(self.order_history_df)
            model = OrderHistoryPandasModel(df_for_model)
            self.order_history_tableview.setModel(model)

    @property
    def to_date(self):
        return self.__to_date

    @to_date.setter
    def to_date(self, value):
        self.__to_date = value
        if self.order_history_df is not None:
            df_for_model = self.filtering_df(self.order_history_df)
            model = OrderHistoryPandasModel(df_for_model)
            self.order_history_tableview.setModel(model)

    @property
    def loading_progress_order_history(self):
        return self.__loading_progress_order_history

    @loading_progress_order_history.setter
    def loading_progress_order_history(self, value):
        self.__loading_progress_order_history = value
        self.loading_progress_order_history_changed.emit(value)  # noqa

    @property
    def order_history_df(self):
        return self.__order_history_df

    @order_history_df.setter
    def order_history_df(self, value):
        self.__order_history_df = value
        self.order_history_df_changed.emit()  # noqa

    order_history_df_changed = QtCore.Signal()
    loading_progress_order_history_changed = QtCore.Signal(int)

    def __init__(self, upbit_client, krw_markets, btc_markets, parent=None):
        super().__init__(parent=parent)
        self.upbit_client = upbit_client
        self.krw_markets = krw_markets
        self.btc_markets = btc_markets
        self.__order_history_df = pd.DataFrame(columns=["????????????", "??????", "??????", "????????????", "????????????", "????????????", "?????????", "????????????"])
        self.__from_date = QtCore.QDate.currentDate()
        self.__to_date = QtCore.QDate.currentDate()
        self.__loading_progress_order_history = 0.0

        # Thread
        self.thread_pool = QtCore.QThreadPool.globalInstance()

        # Loading Spinner
        self.spinner = WaitingSpinner(self)

        # ???????????? ??????
        self.refresh_btn = QtWidgets.QPushButton(u"\u21BB", parent=self)
        self.refresh_btn.setStyleSheet("font-size: 20px;")
        self.refresh_btn.setFixedHeight(58)
        self.refresh_btn.clicked.connect(self.refresh_btn_clicked)

        # Ticker Filter
        self.all_ticker_btn = QtWidgets.QPushButton("??????", parent=self)
        self.all_ticker_btn.setFixedHeight(25)
        self.all_ticker_btn.setCheckable(True)
        self.krw_ticker_btn = QtWidgets.QPushButton("KRW", parent=self)
        self.krw_ticker_btn.setFixedHeight(25)
        self.krw_ticker_btn.setCheckable(True)
        self.btc_ticker_btn = QtWidgets.QPushButton("BTC", parent=self)
        self.btc_ticker_btn.setFixedHeight(25)
        self.btc_ticker_btn.setCheckable(True)

        self.ticker_btn_group = QtWidgets.QButtonGroup(parent=self)
        self.ticker_btn_group.addButton(self.all_ticker_btn, 0)
        self.ticker_btn_group.addButton(self.krw_ticker_btn, 1)
        self.ticker_btn_group.addButton(self.btc_ticker_btn, 2)
        self.ticker_btn_group.buttonClicked.connect(self.ticker_btn_clicked)  # noqa

        self.ticker_filter_combobox = QtWidgets.QComboBox(parent=self)
        self.ticker_filter_combobox.view().setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.ticker_filter_combobox.currentIndexChanged.connect(
            self.ticker_filter_combobox_currentIndex_changed)  # noqa

        ticker_groupbox_layout = QtWidgets.QGridLayout()
        ticker_groupbox_layout.addWidget(self.all_ticker_btn, 0, 0, 0, 1)
        ticker_groupbox_layout.addWidget(self.krw_ticker_btn, 0, 1, 0, 1)
        ticker_groupbox_layout.addWidget(self.btc_ticker_btn, 0, 2, 0, 1)
        ticker_groupbox_layout.addWidget(self.ticker_filter_combobox, 0, 3, 0, 7)
        ticker_groupbox = QtWidgets.QGroupBox("Tiker filter", parent=self)
        ticker_groupbox.setStyleSheet("QGroupBox{font-size: 12px;}")
        ticker_groupbox.setLayout(ticker_groupbox_layout)

        # ??????/?????? ??????
        self.all_side_btn = QtWidgets.QPushButton("??????", parent=self)
        self.all_side_btn.setFixedHeight(25)
        self.all_side_btn.setCheckable(True)
        self.buy_side_btn = QtWidgets.QPushButton("??????", parent=self)
        self.buy_side_btn.setFixedHeight(25)
        self.buy_side_btn.setCheckable(True)
        self.sell_side_btn = QtWidgets.QPushButton("??????", parent=self)
        self.sell_side_btn.setFixedHeight(25)
        self.sell_side_btn.setCheckable(True)

        self.side_btn_group = QtWidgets.QButtonGroup(parent=self)
        self.side_btn_group.addButton(self.all_side_btn, 0)
        self.side_btn_group.addButton(self.buy_side_btn, 1)
        self.side_btn_group.addButton(self.sell_side_btn, 2)
        self.side_btn_group.buttonClicked.connect(self.side_btn_clicked)  # noqa

        side_groupbox_layout = QtWidgets.QGridLayout()
        side_groupbox_layout.addWidget(self.all_side_btn, 0, 0, 0, 1)
        side_groupbox_layout.addWidget(self.buy_side_btn, 0, 1, 0, 1)
        side_groupbox_layout.addWidget(self.sell_side_btn, 0, 2, 0, 1)
        side_groupbox = QtWidgets.QGroupBox("Side filter", parent=self)
        side_groupbox.setStyleSheet("QGroupBox{font-size: 12px;}")
        side_groupbox.setLayout(side_groupbox_layout)

        top_btn_layout = QtWidgets.QGridLayout()
        top_btn_layout.addWidget(ticker_groupbox, 0, 0, 0, 10)
        top_btn_layout.addWidget(side_groupbox, 0, 10, 0, 6)
        top_btn_layout.addWidget(QtWidgets.QWidget(parent=self), 0, 16, 0, 3)
        top_btn_layout.addWidget(self.refresh_btn, 0, 19, 0, 1, alignment=QtCore.Qt.AlignBottom)  # noqa

        # ????????? ?????? ?????? ??????
        self.today_btn = QtWidgets.QPushButton("??????", parent=self)
        self.all_ticker_btn.setFixedHeight(25)
        self.today_btn.setCheckable(True)
        self.week1_btn = QtWidgets.QPushButton("1??????", parent=self)
        self.all_ticker_btn.setFixedHeight(25)
        self.week1_btn.setCheckable(True)
        self.week2_btn = QtWidgets.QPushButton("2??????", parent=self)
        self.all_ticker_btn.setFixedHeight(25)
        self.week2_btn.setCheckable(True)
        self.month1_btn = QtWidgets.QPushButton("1??????", parent=self)
        self.all_ticker_btn.setFixedHeight(25)
        self.month1_btn.setCheckable(True)
        self.month3_btn = QtWidgets.QPushButton("3??????", parent=self)
        self.all_ticker_btn.setFixedHeight(25)
        self.month3_btn.setCheckable(True)
        self.month6_btn = QtWidgets.QPushButton("6??????", parent=self)
        self.all_ticker_btn.setFixedHeight(25)
        self.month6_btn.setCheckable(True)
        self.year1_btn = QtWidgets.QPushButton("1???", parent=self)
        self.all_ticker_btn.setFixedHeight(25)
        self.year1_btn.setCheckable(True)

        self.period_btn_group = QtWidgets.QButtonGroup(parent=self)
        self.period_btn_group.addButton(self.today_btn, 0)
        self.period_btn_group.addButton(self.week1_btn, 1)
        self.period_btn_group.addButton(self.week2_btn, 2)
        self.period_btn_group.addButton(self.month1_btn, 3)
        self.period_btn_group.addButton(self.month3_btn, 4)
        self.period_btn_group.addButton(self.month6_btn, 5)
        self.period_btn_group.addButton(self.year1_btn, 6)
        self.period_btn_group.buttonClicked.connect(self.period_btn_clicked)  # noqa

        self.period_btn_layout = QtWidgets.QHBoxLayout()
        self.period_btn_layout.addWidget(self.today_btn)
        self.period_btn_layout.addWidget(self.week1_btn)
        self.period_btn_layout.addWidget(self.week2_btn)
        self.period_btn_layout.addWidget(self.month1_btn)
        self.period_btn_layout.addWidget(self.month3_btn)
        self.period_btn_layout.addWidget(self.month6_btn)
        self.period_btn_layout.addWidget(self.year1_btn)

        # ?????? ?????? ?????? ??????
        self.from_date_btn = QtWidgets.QPushButton(
            f'{self.from_date.year()}.{self.from_date.month():02d}.{self.from_date.day():02d}',
            parent=self)
        self.from_date_btn.setCheckable(True)
        self.to_date_btn = QtWidgets.QPushButton(
            f'{self.to_date.year()}.{self.to_date.month():02d}.{self.to_date.day():02d}',
            parent=self)
        self.to_date_btn.setCheckable(True)
        self.from_date_btn.clicked.connect(self.from_btn_clicked)
        self.to_date_btn.clicked.connect(self.to_btn_clicked)

        self.date_btn_layout = QtWidgets.QGridLayout()
        self.date_btn_layout.addWidget(self.from_date_btn, 0, 0, 1, 5)
        self.date_btn_layout.addWidget(QtWidgets.QLabel(" ~ ", alignment=QtCore.Qt.AlignCenter,  parent=self), 0, 5, 1, 1)
        self.date_btn_layout.addWidget(self.to_date_btn, 0, 6, 1, 5)

        period_groupbox_layout = QtWidgets.QVBoxLayout()
        period_groupbox_layout.addLayout(self.period_btn_layout)
        period_groupbox_layout.addLayout(self.date_btn_layout)
        period_groupbox = QtWidgets.QGroupBox("Date filter", parent=self)
        period_groupbox.setStyleSheet("QGroupBox{font-size: 12px;}")
        period_groupbox.setLayout(period_groupbox_layout)

        # ????????????
        self.from_calender_widget = CalenderWidget()
        self.from_calender_widget.setMinimumWidth(400)
        self.from_calender_widget.setMinimumHeight(300)
        self.from_calender_widget.setWindowTitle("????????????")
        self.from_calender_widget.setDateRange(QtCore.QDate(2019, 1, 1), QtCore.QDate.currentDate())
        self.from_calender_widget.clicked.connect(self.from_date_clicked)  # noqa
        self.from_calender_widget.closed.connect(lambda: self.from_date_btn.setChecked(False))

        self.to_calender_widget = CalenderWidget()
        self.to_calender_widget.setMinimumWidth(400)
        self.to_calender_widget.setMinimumHeight(300)
        self.to_calender_widget.setWindowTitle("????????????")
        self.to_calender_widget.clicked.connect(self.to_date_clicked)  # noqa
        self.to_calender_widget.closed.connect(lambda: self.to_date_btn.setChecked(False))

        # ?????????
        self.order_history_tableview = OrderHistoryTableView()
        self.order_history_tableview.verticalScrollBar().setFixedWidth(10)
        model = OrderHistoryPandasModel(self.order_history_df)
        self.order_history_tableview.setModel(model)
        self.order_history_tableview.horizontalHeader().setStretchLastSection(True)
        self.order_history_tableview.setColumnWidth(0, 170)  # ????????????
        self.order_history_tableview.setColumnWidth(1, 100)  # ??????
        self.order_history_tableview.setColumnWidth(2, 60)  # ??????
        self.order_history_tableview.setColumnWidth(3, 170)  # ????????????
        self.order_history_tableview.setColumnWidth(4, 170)  # ????????????
        self.order_history_tableview.setColumnWidth(5, 170)  # ????????????
        self.order_history_tableview.setColumnWidth(6, 140)  # ?????????
        self.order_history_tableview.setColumnWidth(7, 170)  # ?????????
        self.order_history_tableview.doubleClicked.connect(self.table_double_clicked)  # noqa

        self.table_layout = QtWidgets.QHBoxLayout()
        self.table_layout.addWidget(self.order_history_tableview)

        # ????????????
        main_layout = QtWidgets.QVBoxLayout(parent=self)
        main_layout.addLayout(top_btn_layout)
        main_layout.addWidget(period_groupbox)
        main_layout.addLayout(self.table_layout)
        self.setLayout(main_layout)

        self.all_ticker_btn.setChecked(True)
        self.ticker_btn_clicked(self.all_ticker_btn)
        self.all_side_btn.setChecked(True)
        self.ticker_btn_clicked(self.all_side_btn)
        self.today_btn.setChecked(True)
        self.period_btn_clicked(self.today_btn)
        self.refresh_btn_clicked()

    @QtCore.Slot()
    def table_double_clicked(self, qmodel_index):
        col = qmodel_index.column()
        header_text = qmodel_index.model().headerData(col, QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole)
        cell_text = qmodel_index.data()
        if header_text == "????????????":
            self.unchecked_date_btn_group()
            self.from_date = QtCore.QDate.fromString(cell_text.split(' ')[0], "yyyy/MM/dd")
            self.to_date = QtCore.QDate.fromString(cell_text.split(' ')[0], "yyyy/MM/dd")
            self.from_date_btn.setText(
                f'{self.from_date.year()}.{self.from_date.month():02d}.{self.from_date.day():02d}')
            self.to_date_btn.setText(f'{self.to_date.year()}.{self.to_date.month():02d}.{self.to_date.day():02d}')
        elif header_text == "??????":
            if cell_text.startswith('KRW-'):
                self.krw_ticker_btn.setChecked(True)
                self.ticker_btn_clicked(self.krw_ticker_btn)
            elif cell_text.startswith('BTC-'):
                self.btc_ticker_btn.setChecked(True)
                self.ticker_btn_clicked(self.btc_ticker_btn)
            index = self.ticker_filter_combobox.findText(cell_text, QtCore.Qt.MatchContains)  # noqa
            if index >= 0:
                self.ticker_filter_combobox.setCurrentIndex(index)
        elif header_text == "??????":
            if cell_text == "??????":
                self.buy_side_btn.setChecked(True)
                self.side_btn_clicked(self.buy_side_btn)
            elif cell_text == "??????":
                self.sell_side_btn.setChecked(True)
                self.side_btn_clicked(self.sell_side_btn)

    @QtCore.Slot()
    def ticker_filter_combobox_currentIndex_changed(self):  # noqa
        if self.order_history_df is not None:
            df_for_model = self.filtering_df(self.order_history_df)
            model = OrderHistoryPandasModel(df_for_model)
            self.order_history_tableview.setModel(model)

    @QtCore.Slot()
    def refresh_btn_clicked(self):
        def worker_fn():
            self.get_all_orders_by_upbit()

        def finish_fn():
            self.stop_spinner()

        self.play_spinner()
        worker = Worker(worker_fn)
        worker.signals.finished.connect(finish_fn)
        self.thread_pool.start(worker)

    @QtCore.Slot(int)
    def side_btn_clicked(self, btn):  # noqa
        if self.order_history_df is not None:
            df_for_model = self.filtering_df(self.order_history_df)
            model = OrderHistoryPandasModel(df_for_model)
            self.order_history_tableview.setModel(model)

    @QtCore.Slot(int)
    def ticker_btn_clicked(self, btn):
        id = self.ticker_btn_group.id(btn)
        if id == 0:
            self.ticker_filter_combobox.setEnabled(False)
            self.ticker_filter_combobox.clear()
            self.ticker_filter_combobox.addItem("KRW/BTC ??????")
        elif id == 1:
            self.ticker_filter_combobox.setEnabled(True)
            self.ticker_filter_combobox.clear()
            items_list = [f"{i['korean_name']} ({i['market']})" for i in self.krw_markets]
            self.ticker_filter_combobox.addItem("KRW ??????")
            self.ticker_filter_combobox.addItems(items_list)
        elif id == 2:
            self.ticker_filter_combobox.setEnabled(True)
            self.ticker_filter_combobox.clear()
            items_list = [f"{i['korean_name']} ({i['market']})" for i in self.btc_markets]
            self.ticker_filter_combobox.addItem("BTC ??????")
            self.ticker_filter_combobox.addItems(items_list)

        if self.order_history_df is not None:
            df_for_model = self.filtering_df(self.order_history_df)
            model = OrderHistoryPandasModel(df_for_model)
            self.order_history_tableview.setModel(model)

    @QtCore.Slot(int)
    def period_btn_clicked(self, btn):
        id = self.period_btn_group.id(btn)
        self.to_date = QtCore.QDate.currentDate()
        self.to_date_btn.setChecked(False)
        self.from_date_btn.setChecked(False)
        if id == 0:
            self.from_date = QtCore.QDate.currentDate()
        elif id == 1:
            self.from_date = QtCore.QDate.currentDate().addDays(-7)
        elif id == 2:
            self.from_date = QtCore.QDate.currentDate().addDays(-14)
        elif id == 3:
            self.from_date = QtCore.QDate.currentDate().addMonths(-1)
        elif id == 4:
            self.from_date = QtCore.QDate.currentDate().addMonths(-3)
        elif id == 5:
            self.from_date = QtCore.QDate.currentDate().addMonths(-6)
        elif id == 6:
            self.from_date = QtCore.QDate.currentDate().addYears(-1)

        self.from_date_btn.setText(f'{self.from_date.year()}.{self.from_date.month():02d}.{self.from_date.day():02d}')
        self.to_date_btn.setText(f'{self.to_date.year()}.{self.to_date.month():02d}.{self.to_date.day():02d}')

    @QtCore.Slot()
    def from_btn_clicked(self):
        self.unchecked_date_btn_group()
        self.to_date_btn.setChecked(False)

        self.to_calender_widget.hide()
        self.from_calender_widget.show()
        self.from_calender_widget.setSelectedDate(self.from_date)

    @QtCore.Slot()
    def to_btn_clicked(self):
        self.unchecked_date_btn_group()
        self.from_date_btn.setChecked(False)

        self.from_calender_widget.hide()
        self.to_calender_widget.show()
        self.to_calender_widget.setSelectedDate(self.to_date)

    @QtCore.Slot(QtCore.QDate)
    def from_date_clicked(self, date):
        self.from_date = date
        self.from_date_btn.setText(f'{self.from_date.year()}.{self.from_date.month():02d}.{self.from_date.day():02d}')
        self.from_calender_widget.hide()
        self.from_date_btn.setChecked(False)
        self.to_calender_widget.setDateRange(self.from_date, QtCore.QDate.currentDate())

    @QtCore.Slot(QtCore.QDate)
    def to_date_clicked(self, date):
        self.to_date = date
        self.to_date_btn.setText(f'{self.to_date.year()}.{self.to_date.month():02d}.{self.to_date.day():02d}')
        self.to_calender_widget.hide()
        self.to_date_btn.setChecked(False)
        self.from_calender_widget.setDateRange(QtCore.QDate(2019, 1, 1), self.to_date)

    def get_all_orders_by_upbit(self):
        # ?????? ?????? History ??????
        _order_info_all = []
        page = 1
        while True:
            orders = self.upbit_client.Order.Order_info_all(page=page, limit=100, states=["done", "cancel"])['result']
            _order_info_all = _order_info_all + orders
            page += 1
            if len(orders) < 100:
                break
        _order_info_all = [order for order in _order_info_all if order['trades_count'] > 0]

        # ?????? ????????? ?????? Detailed info ?????? ??? ????????????
        for i, order in enumerate(_order_info_all):
            detailed_order = self.upbit_client.Order.Order_info(uuid=order['uuid'])['result']
            if 'trades' in detailed_order and detailed_order['trades']:
                df_trades = pd.DataFrame(detailed_order['trades'])
                df_trades = df_trades.astype({'funds': float,
                                              'price': float,
                                              'volume': float})
                fund = df_trades['funds'].sum()
                trading_price = df_trades['price'].sum() / detailed_order['trades_count']
                trading_volume = df_trades['volume'].sum()
                order['fund'] = fund
                order['trading_price'] = trading_price
                order['trading_volume'] = trading_volume
                if order['side'] == 'ask':  # ????????? ???????????? = ???????????? - ?????????
                    order['executed_fund'] = order['fund'] - float(order['paid_fee'])
                else:  # ????????? ???????????? = ???????????? + ?????????
                    order['executed_fund'] = order['fund'] + float(order['paid_fee'])
            # single dict to df??? ??????
            df = pd.DataFrame([order])
            df.loc[(df.side == 'bid'), 'side'] = '??????'
            df.loc[(df.side == 'ask'), 'side'] = '??????'

            df.drop(['uuid', 'ord_type', 'price', 'state', 'trades_count', 'volume', 'executed_volume',
                     'remaining_volume', 'reserved_fee', 'remaining_fee', 'locked'], axis=1, inplace=True, errors='ignore')
            df.rename(columns={'side': '??????', 'trading_price': '????????????', 'market': '??????', 'created_at': '????????????',
                               'paid_fee': '?????????', 'fund': '????????????', 'trading_volume': '????????????',
                               'executed_fund': '????????????'}, inplace=True)
            df = df.reindex(columns=['????????????', '??????', '??????', '????????????', '????????????', '????????????', '?????????', '????????????'])
            df['????????????'] = pd.to_datetime(df['????????????'])
            df = df.astype({'?????????': float})

            # update progress bar in main
            self.loading_progress_order_history = (i + 1) / len(_order_info_all) * 100
            # ??????
            self.order_history_df = pd.concat([self.order_history_df, df], ignore_index=True)
            self.order_history_df_changed.emit()  # noqa

    def play_spinner(self):
        self.refresh_btn.setEnabled(False)
        self.spinner.show()
        self.spinner.raise_()
        self.spinner.start()

    def stop_spinner(self):
        self.spinner.stop()
        self.refresh_btn.setEnabled(True)

    def unchecked_date_btn_group(self):
        if self.period_btn_group.checkedButton():
            self.period_btn_group.setExclusive(False)
            self.period_btn_group.checkedButton().setChecked(False)
            self.period_btn_group.setExclusive(True)

    def update_table_model(self):
        df_for_model = self.filtering_df(self.order_history_df)
        model = OrderHistoryPandasModel(df_for_model)
        self.order_history_tableview.setModel(model)

    def filtering_df(self, df):
        result_df = df.sort_values(by='????????????', ascending=False)

        # ?????? ?????????
        from_datetime = QtCore.QDateTime.fromString(f'{self.from_date.toString("yyyy-MM-dd")} 00:00:00',
                                                    "yyyy-MM-dd hh:mm:ss")
        to_datetime = QtCore.QDateTime.fromString(f'{self.to_date.toString("yyyy-MM-dd")} 23:59:59',
                                                  "yyyy-MM-dd hh:mm:ss")
        from_datetime = from_datetime.toPython().astimezone(timezone('Asia/Seoul'))
        to_datetime = to_datetime.toPython().astimezone(timezone('Asia/Seoul'))

        result_df = result_df.query(
            '@from_datetime <= ???????????? <= @to_datetime'
        )

        # ?????? ?????? ?????????
        side_btn_id = self.side_btn_group.checkedId()
        if side_btn_id == 0:  # ??????
            pass
        elif side_btn_id == 1:  # ??????
            result_df = result_df.query('??????.str.contains("??????")')
        elif side_btn_id == 2:  # ??????
            result_df = result_df.query('??????.str.contains("??????")')

        # ?????? ?????????
        if self.ticker_filter_combobox.currentText() == "KRW/BTC ??????":
            pass
        elif self.ticker_filter_combobox.currentText() == "KRW ??????":
            result_df = result_df.query('??????.str.contains("KRW-")')
        elif self.ticker_filter_combobox.currentText() == "BTC ??????":
            result_df = result_df.query('??????.str.contains("BTC-")')
        else:  # ?????? ?????? ??????
            temp_list = re.findall('\((KRW-[^)]+|BTC-[^)]+)\)', self.ticker_filter_combobox.currentText())  # noqa
            if temp_list:
                target_ticker = temp_list[0]  # noqa
                result_df = result_df.query('??????.str.contains(@target_ticker)')
            else:
                return result_df.dropna()

        # index ??????
        result_df = result_df.reset_index(drop=True)
        return result_df
