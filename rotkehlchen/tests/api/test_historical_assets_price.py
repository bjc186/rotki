import random

from http import HTTPStatus
import pytest
import requests

from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task_with_result,
    assert_error_response,
)


@pytest.mark.parametrize('mocked_price_queries', [{
    'BTC': {
        'USD': {
            1579543935: FVal('30000'),
            1611166335: FVal('35000'),
        },
    },
    'USD': {'USD': {1579543935: FVal('1')}},
    'GBP': {
        'USD': {
            1548007935: FVal('1.25'),
            1611166335: FVal('1.27'),
        },
    },
    'XRP': {'USD': {1611166335: FVal('0')}},
}])
def test_get_historical_assets_price(rotkehlchen_api_server):
    """Test given a list of asset-timestamp tuples it returns the asset price
    at the given timestamp.
    """
    async_query = random.choice([False, True])
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            "historicalassetspriceresource",
        ),
        json={
            'assets_timestamp': [
                ['BTC', 1579543935],
                ['BTC', 1611166335],
                ['USD', 1579543935],
                ['GBP', 1548007935],
                ['GBP', 1611166335],
                ['XRP', 1611166335],
            ],
            'target_asset': 'USD',
            'async_query': async_query,
        },
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
    else:
        result = assert_proper_response_with_result(response)

    assert len(result) == 2
    assert result['assets']['BTC'] == {
        '1579543935': '30000',
        '1611166335': '35000',
    }
    assert result['assets']['USD'] == {'1579543935': '1'}
    assert result['assets']['GBP'] == {
        '1548007935': '1.25',
        '1611166335': '1.27',
    }
    assert result['assets']['XRP'] == {'1611166335': '0'}
    assert result['target_asset'] == 'USD'


def test_set_historical_price(rotkehlchen_api_server, globaldb):

    seur = EthereumToken('0xD71eCFF9342A5Ced620049e616c5035F1dB98620')

    async_query = random.choice([False, True])
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "historicalassetspriceresource",
        ),
        json={
            'from_asset': '_ceth_0xD71eCFF9342A5Ced620049e616c5035F1dB98620',
            'to_asset': 'USD',
            'async_query': async_query,
            'timestamp': 1611166335,
            'price': "1.20",
        },
    )

    if async_query:
        task_id = assert_ok_async_response(response)
        wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
    else:
        assert_proper_response_with_result(response)

    historical_price = globaldb.get_historical_price(
        from_asset=seur,
        to_asset=A_USD,
        timestamp=1611166335,
        max_seconds_distance=10,
    )

    assert historical_price.price == FVal(1.2)
    assert historical_price.from_asset == seur
    assert historical_price.to_asset == A_USD

    # Test with an unkown asset
    async_query = False
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "historicalassetspriceresource",
        ),
        json={
            'from_asset': '_ceth_0xD71eCFF9342A5Ced620049e616c5035F1dB98621',
            'to_asset': 'USD',
            'async_query': async_query,
            'timestamp': 1611166335,
            'price': "1.20",
        },
    )

    assert_error_response(
        response=response,
        contained_in_msg='Unknown asset',
        status_code=HTTPStatus.BAD_REQUEST,
    )
