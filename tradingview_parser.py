import os, pyperclip
from dotenv import load_dotenv
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, WebDriverException, StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from decorators import repeat_if_fail, ignore_if_fail, execute_if_fail
from parser import Parser

load_dotenv()

def _(s:str):
    return s.lower().replace(" ", "")

RAISED = "raised"
LOWERED = "lowered"
INITIATED = "initiated"

WORKING = "working"
INACTIVE = "inactive"
CANCELED = "cancelled"
FILLED = "filled"
REJECTED = "rejected"

STOP = "stop"
STOP_LOSS = "stop loss"
TAKE_PROFIT = "take profit"

SELL = "sell"
BUY = "buy"

class TradingViewParser(Parser):
    base_url = "https://www.tradingview.com/"
    chart_url = base_url + "chart/G9fChrEy/"
    source_name = "tradingview"
    resistance = None
    support = None
    martingale = False
    current_turn = 0
    placing_time = None

    user_menu_btn = (By.XPATH, '//button[contains(@aria-label, "Open user menu")]')
    sign_in_btn = (By.XPATH, '//button[contains(@data-name, "header-user-menu-sign-in")]')
    email_btn = (By.XPATH, '//button[contains(@name, "Email")]')
    username_input = (By.ID, "id_username")
    password_input = (By.ID, "id_password")
    login_btn = (By.XPATH, '//button[contains(@data-overflow-tooltip-text, "Sign in")]')
    data_panel = (By.XPATH, '//div[contains(@data-name, "order-panel")]')
    sell_btn = (By.XPATH, '//div[contains(@data-name, "side-control-sell")]')
    buy_btn = (By.XPATH, '//div[contains(@data-name, "side-control-buy")]')
    object_tree_btn = (By.XPATH, '//button[contains(@data-name, "object_tree") and contains(@data-tooltip, "Object Tree and Data Window")]')
    trading_panel_header = (By.CLASS_NAME, "trading-panel-header-LlInYWMC")
    broker_btn = (By.XPATH, '//div[contains(@data-broker, "Paper")]')
    connect_to_broker_btn = (By.XPATH, '//button[contains(@name, "broker-login-submit-button")]')
    resistance_el = (By.XPATH, '//div[contains(@class, "headerTitle-_gbYDtbd") and contains(text(), "Support and Resistance Levels")]//following::div[contains(@class, "itemTitle-_gbYDtbd") and contains(text(), "Resistance")]/following-sibling::div/span')
    support_el = (By.XPATH, '//div[contains(@class, "headerTitle-_gbYDtbd") and contains(text(), "Support and Resistance Levels")]//following::div[contains(@class, "itemTitle-_gbYDtbd") and contains(text(), "Support")]/following-sibling::div/span')
    data_tree_btn = (By.ID, "data-window")
    data_tree_widget = (By.XPATH, '//div[contains(@class, "widgetbar-widget widgetbar-widget-object_tree")]')
    order_panel = (By.XPATH, '//div[contains(@data-name, "order-panel")]')
    stop_btn = (By.ID, "Stop")
    close_order_panel_btn = (By.XPATH, '//button[contains(@data-name, "button-close")]')
    order_quantity_input = (By.XPATH, '//input[contains(@id, "order-ticket-quantity-input")]')
    take_profit_checkbox = (By.XPATH, '//input[contains(@data-name, "order-ticket-profit-checkbox-bracket")]/..')
    stop_loss_checkbox = (By.XPATH, '//input[contains(@data-name, "order-ticket-loss-checkbox-bracket")]/..')
    take_profit_panel = (By.XPATH, '//div[contains(@class, "bracketControl-Llv4yjs6")]')
    stop_loss_panel = (By.XPATH, '//div[contains(@class, "bracketControl-Llv4yjs6 rightBlock-Llv4yjs6")]')
    place_order_btn = (By.XPATH, '//button[contains(@data-name, "place-and-modify-button")]')
    orders_btn = (By.XPATH, '//button[contains(@id, "orders")]')
    orders_table = (By.XPATH, '//table[contains(@data-selector, "table")]')
    order_status = (By.XPATH, '//td[contains(@data-label, "Status")]')
    order_type = (By.XPATH, '//td[contains(@data-label, "Type")]')
    order_units = (By.XPATH, '//td[contains(@data-label, "Qty")]')
    order_placing_time = (By.XPATH, '//td[contains(@data-label, "Placing Time")]')
    order_side = (By.XPATH, '//td[contains(@data-label, "Side")]')
    order_price = (By.XPATH, '//span[contains(@class, "absolutePriceControl-HcMnXcBP")]//input[contains(@class, "input-RUSovanF")]')

    def __init__(self, init_url=None, db_manager=None, use_driver=True, use_request=False, proxies=[], log=True) -> None:
        super().__init__(init_url, db_manager, use_driver, use_request, proxies, log)
        self.contracts, self.take_profit, self.stop_loss = self.get_settings()
        self.martingale_mode, self.wheel, self.martingale_coef = self.get_martingale_settings()

    @repeat_if_fail(NoSuchElementException, 5)
    def perform_login(self):
        self.driver.get(self.base_url)
        self.wait(5)
        self.click_on_element(*self.user_menu_btn)
        self.click_on_element(*self.sign_in_btn)
        self.click_on_element(*self.email_btn)
        self.fill_input_element(*self.username_input, self.username)
        self.fill_input_element(*self.password_input, self.password)
        self.click_on_element(*self.login_btn)
        self.wait(35)

    def press_shift_t(self):
        pressing = ActionChains(self.driver)
        pressing.key_down(Keys.SHIFT).send_keys("t").key_up(Keys.SHIFT).perform()
        self.wait(0.3)

    def set_default_contracts(self):
        self.contracts = os.getenv("CONTRACTS_QUANTITY")

    def take_screenshot(self):
        date = self.get_current_date()
        self.driver.save_screenshot(f"screenshots/{date}.png")
        self.logger.info("Screenshot has been taken.")

    def get_difference(self, cur, prev):
        if not prev: 
            return INITIATED
        if cur == prev: 
            return None
        if cur > prev:
            return RAISED
        if cur < prev:
            return LOWERED
        
    @execute_if_fail(TypeError, lambda: (None, None))
    @repeat_if_fail([NoSuchElementException, TypeError], 7)
    def refresh_support_and_resistance(self):
        items = self.driver.find_elements(By.CLASS_NAME, "item-_gbYDtbd")
        for item in items:
            insides = item.find_elements(By.TAG_NAME, "div")
            if "Resistance" in insides[0].text:
                current_resistance = float(insides[1].text.replace(",",""))
            if "Support" in insides[0].text:
                current_support = float(insides[1].text.replace(",",""))
        support_diff = self.get_difference(current_support, self.support)
        resistance_diff = self.get_difference(current_resistance, self.resistance)
        if support_diff: 
            self.support = current_support
            self.logger.info(f"Support changed. Status: {support_diff.capitalize()}")
        if resistance_diff: 
            self.resistance = current_resistance
            self.logger.info(f"Resistance changed. Status: {resistance_diff.capitalize()}")
        return support_diff, resistance_diff

    @ignore_if_fail(NoSuchElementException)
    @repeat_if_fail(NoSuchElementException, 7)
    @repeat_if_fail(NoSuchElementException, 10)
    def connect_to_broker(self):
        brokers = self.driver.find_element(By.CLASS_NAME, "brokers-g8EG8iFB")
        if not brokers:
            self.press_shift_t()
        self.click_on_element(*self.broker_btn)
        self.click_on_element(*self.connect_to_broker_btn)

    def get_settings(self):
        contracts = os.getenv("CONTRACTS_QUANTITY")
        take_profit = float(os.getenv("TAKE_PROFIT"))
        stop_loss = float(os.getenv("STOP"))
        return contracts, take_profit, stop_loss
    
    def get_martingale_settings(self):
        mode = os.getenv("MARTINGALE_MODE")
        wheel = int(os.getenv('MARTINGALE_WHEEL'))
        coef = int(os.getenv('MARTINGALE_COEF'))
        return mode, range(1, wheel+1), coef
    
    def el_paste_text(self, el, text):
        pyperclip.copy(str(text))
        el.send_keys(Keys.CONTROL, 'a')
        el.send_keys(Keys.CONTROL, 'v')
        self.wait(0.3)

    def open_data_tree(self):
        try:
            self.driver.find_element(*self.data_tree_btn)
        except NoSuchElementException:
            self.click_on_element(*self.object_tree_btn)
        self.click_on_element(*self.data_tree_btn)
        self.wait(3,7)

    def calculate_resistance(self):
        price_to_buy = round(self.resistance - (self.take_profit / 10), 2)
        loss_price = round(price_to_buy - self.stop_loss, 2)
        return price_to_buy, loss_price
    
    def calculate_support(self):
        price_to_buy = round(self.resistance + (self.take_profit / 10), 2)
        loss_price = round(price_to_buy + self.stop_loss, 2)
        return price_to_buy, loss_price
    
    @execute_if_fail(NoSuchElementException, lambda: False)
    def check_checkbox(self, el):
        el.find_element(By.CLASS_NAME, "checked-ywH2tsV_")
        return True

    @repeat_if_fail(NoSuchElementException, 3)
    def prepare_order(self, buy=False):
        self.logger.info("Preparing order...")
        try: 
            self.driver.find_element(*self.order_panel)
        except NoSuchElementException:
            self.press_shift_t()
        self.wait(0.5)
        stop_btn = self.driver.find_element(*self.stop_btn)
        clicked = stop_btn.get_attribute("aria-selected")
        if not clicked:
            self.click_on_element(*self.stop_btn)
        if buy:
            self.click_on_element(*self.buy_btn)
            price, loss = self.calculate_resistance()
        else:
            self.click_on_element(*self.sell_btn)
            price, loss = self.calculate_support()
        self.paste_text(*self.order_price, price)
        self.paste_text(*self.order_quantity_input, self.contracts)
        tpb = self.driver.find_element(*self.take_profit_checkbox)
        if not self.check_checkbox(tpb): 
            tpb.click()
        slb = self.driver.find_element(*self.stop_loss_checkbox)
        if not self.check_checkbox(slb): 
            slb.click()
        take_profit_panel = self.driver.find_element(*self.take_profit_panel)
        stop_loss_panel = self.driver.find_element(*self.stop_loss_panel)
        self.el_paste_text(take_profit_panel.find_elements(By.TAG_NAME, "input")[0], self.take_profit)
        self.el_paste_text(stop_loss_panel.find_elements(By.TAG_NAME, "input")[0], self.stop_loss)
        place_order_btn = self.driver.find_element(*self.place_order_btn)
        self.logger.info(f"Order is prepared. Price: {price}, contracts: {self.contracts}")
        return place_order_btn
    
    @ignore_if_fail(StaleElementReferenceException)
    def make_order(self, refresh=None):
        if not refresh:
            support_diff, resistance_diff = self.refresh_support_and_resistance()
            if ((not support_diff and not resistance_diff) 
                or (support_diff == INITIATED and resistance_diff == INITIATED)):
                return False
        else:
            support_diff, resistance_diff = refresh
        buy = True if resistance_diff else False
        place_order_btn = self.prepare_order(buy=buy)
        while True:
            self.wait(0.5)
            disabled = place_order_btn.get_attribute('disabled')
            support_diff, resistance_diff = self.refresh_support_and_resistance()
            if disabled and (not support_diff and not resistance_diff):
                self.logger.info("Waiting for order to activate.")
            if disabled and (support_diff or resistance_diff):
                self.logger.info(f"{'Support level has been ' + support_diff if support_diff else 'Resistnance level has been ' + resistance_diff}, re-ordering.")
                return self.make_order(refresh=(support_diff, resistance_diff))
            if not disabled and (not support_diff and not resistance_diff):
                self.logger.info("Sending order!")
                place_order_btn.click()
                self.wait(0.7)
                self.press_shift_t()
                return True
    
    @ignore_if_fail(ValueError)
    @execute_if_fail(NoSuchElementException, lambda: (REJECTED, None, None, None))
    @repeat_if_fail((NoSuchElementException, ElementClickInterceptedException), 5)
    def check_order_status(self):
        status, type, units, side = None, None, None, None
        self.click_on_element(*self.orders_btn)
        table = self.driver.find_element(*self.orders_table).find_element(By.TAG_NAME, "tbody")
        current_order:list[WebElement] = []
        for i in range(3):
            try:
                current_order.append(table.find_elements(By.TAG_NAME, "tr")[i])
            except IndexError:
                pass
        if not current_order: 
            raise NoSuchElementException
        placing_time = current_order[0].find_element(*self.order_placing_time).text
        current_order = [order for order in current_order if order.find_element(*self.order_placing_time).text == placing_time]
        for order in current_order:
            o_status = order.find_element(*self.order_status).text
            o_type = order.find_element(*self.order_type).text

            if self.martingale and self.martingale_mode == "rigid":
                if self.placing_time == placing_time:
                    return REJECTED, None, None, order.find_element(*self.order_side).text
            if _(o_status) == _(FILLED) and (_(o_type) == _(STOP_LOSS) 
                                            or _(o_type) == _(TAKE_PROFIT)):
                status, type = o_status, o_type
                self.logger.info(f"Order has been {_(status)} with type {type}.")
                if _(o_type) == _(STOP_LOSS):
                    self.take_screenshot()
                    units, side = int(order.find_element(*self.order_units).text), order.find_element(*self.order_side).text
                    self.placing_time = placing_time
                    self.activate_martingale()        
            elif _(o_status) == _(CANCELED) and len(current_order) < 3 and (_(o_type) == _(STOP_LOSS) 
                                                                            or _(o_type) == _(TAKE_PROFIT)):
                    o_type = TAKE_PROFIT if _(o_type) == _(STOP_LOSS) else STOP_LOSS
                    o_status = FILLED
                    status, type = o_status, o_type
                    self.logger.info(f"Order has been {_(status)} with type {type}.")
                    if o_type == STOP_LOSS:
                        self.take_screenshot()
                        units, side = int(order.find_element(*self.order_units).text), order.find_element(*self.order_side).text 
                        self.placing_time = placing_time
                        self.activate_martingale()     
        return status, type, units, side
            
    def watch_order(self):
        self.logger.info("Watching order...")
        while True:
            self.wait(0.7)
            status, type, units, side = self.check_order_status()
            if status and _(status) in (_(FILLED), _(REJECTED)):
                if _(status)  == _(REJECTED):
                    self.logger.info(f"Order has been {_(status)} with type {type}.")
                    date = self.get_current_date()
                    self.driver.save_screenshot(f"screenshots/{date}.png")
                return status, type, units, side
            
    def activate_martingale(self):
        if not self.martingale:
            self.martingale = True 
            self.logger.info(f"Martingale is activated. Martingale mode is {self.martingale_mode}")
            
    def stop_martingale_wheel(self):
        self.current_turn = 0
        self.martingale = False
        self.set_default_contracts()
        self.logger.info("Martingale wheel is stopped.")
        return False
            
    def increment_current_turn(self):
        self.current_turn += 1
        if self.current_turn > max(self.wheel):
            self.logger.info(f"Maringale turns are over. Martingale wheel is about to stop.")
            return self.stop_martingale_wheel()
        self.contracts = self.contracts * self.martingale_coef
        self.logger.info(f"Martingale turn is incremented. Current martingale turn is {self.current_turn}.")
        return True
    
    def decrement_current_turn(self):
        self.logger.info(f"About to decrement martingale turn. Current martingale turn is {self.current_turn}.")
        self.current_turn -= 1
        self.contracts = self.contracts / self.martingale_coef
        if self.current_turn <= 0:
            self.logger.info(f"Maringale turns decrement is impossible.")
            self.current_turn += 1
            self.contracts = self.contracts * self.martingale_coef
        return True
    
    @ignore_if_fail(StaleElementReferenceException)
    def make_martingale(self, side):
        buy = True if _(side) == _(BUY) else False
        place_order_btn = self.prepare_order(buy=buy)
        self.logger.info(f"Maringale order is prepared. Current units is {self.contracts}.")
        while True:
            self.wait(0.5)
            disabled = place_order_btn.get_attribute('disabled')
            if disabled:
                self.logger.info("Waiting for martingale order to activate")
            else:
                self.logger.info(f"Sending martingale!")
                place_order_btn.click()
                self.wait(0.7)
                self.press_shift_t()
                return True
      
    def martingale_wheel(self, units=None, side=SELL):
        if units:
            self.contracts = units
        if self.martingale_mode == "rigid":
            while self.martingale:
                self.wait(0.5)
                incremented = self.increment_current_turn()
                if not incremented:
                    return True
                martingale = self.make_martingale(side)
                if martingale:
                    status, type, units, side = self.watch_order()
                    if _(status) == _(REJECTED):
                        self.logger.info("Martingale has been rejected. Trying again...")
                        self.decrement_current_turn()
                    elif _(type) == _(TAKE_PROFIT):
                        self.stop_martingale_wheel()
                        return True
        if self.martingale_mode == "flexible":
            incremented = self.increment_current_turn()
        return True
            
    def perform_chat_interactions(self):
        self.driver.get(self.chart_url)
        self.wait(5,7)
        self.connect_to_broker()
        self.open_data_tree()
        while True:
            self.wait(0.3)
            order = self.make_order()
            if order: 
                status, type, units, side = self.watch_order()
                if self.martingale and not _(status) == _(REJECTED):
                    self.martingale_wheel(units=units, side=side)

    def parsing_suit(self):
        self.perform_login()
        self.perform_chat_interactions()