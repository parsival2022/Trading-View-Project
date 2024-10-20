import click
from requests.exceptions import ConnectionError, ConnectTimeout
from tradingview_parser import TradingViewParser
from decorators import repeat_if_fail

@repeat_if_fail((ConnectTimeout, 
                 ConnectionError, 
                 ConnectionRefusedError, 
                 ConnectionAbortedError), 7)
def run_bot():
    tradingview = TradingViewParser()
    tradingview.parsing_suit()

@click.group()
def cli():
    pass

@cli.command()
def start_bot():
    run_bot()

if __name__ == "__main__":
    cli()
