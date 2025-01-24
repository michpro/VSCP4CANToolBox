# pylint: disable=line-too-long, missing-module-docstring, missing-function-docstring


import time
import datetime
import asyncio
from crc import Calculator, Crc16
from .message import Message
from .utils import search


MAX_CAN_DLC = 8
THIS_NODE_NICKNAME = 0
MAX_NICKNAME_ID = 254
PROBE_SLEEP = 0.025
PROBE_GAP_SHORT = 0.25
PROBE_GAP_LONG = 1.5
BLOCK_WRITE_GAP = 5.0
PROBE_RETRIES_SHORT = int(PROBE_GAP_SHORT / PROBE_SLEEP)
PROBE_RETRIES_LONG = int(PROBE_GAP_LONG / PROBE_SLEEP)
FIRMWARE_WRITE_ACK_CHECK_RETRIES = int(BLOCK_WRITE_GAP / PROBE_SLEEP)
FIRMWARE_BLOCK_WRITE_RETRIES = 5
FIRMWARE_CHUNK_WRITE_RETRIES = 5
FIRMWARE_FLASH_ERASED_VALUE = 0xFF


_message = Message()
_nodes: list = []
_async_work: bool = False
_this_nickname: int = THIS_NODE_NICKNAME
_scan_progress_observers: list = []


def is_async_work() -> bool:
    return _async_work


def add_scan_progress_observer(observer) -> None:
    if callable(observer):
        _scan_progress_observers.append(observer)


def _update_scan_progress(progress_val) -> None:
    for observer in _scan_progress_observers:
        observer(progress_val)


def guid_str(guid: list) -> str:
    return ":".join(f"{val:02X}" for val in guid)


def set_this_node_nickname(nickname: int):
    global _this_nickname # pylint: disable=global-statement
    _this_nickname = max(min(254, nickname), 0)


def get_this_node_nickname() -> int:
    return _this_nickname


def is_node_on_list(nickname: int) -> bool:
    return not search(nickname, 'id', 'id', _nodes) is None


def append_node(node: dict) -> None:
    _nodes.append(node)


def get_nodes() -> list:
    return _nodes


def clear_nodes() -> None:
    _nodes.clear()


async def probe_node(nickname: int):
    global _async_work # pylint: disable=global-statement
    has_parent = _async_work
    if _async_work is False:
        _async_work = True
        _message.enable_feeder()
        _update_scan_progress(0.0)
    result = None
    vscp_msg = {
        'class':        {'id': None,    'name': 'CLASS1.PROTOCOL'},
        'type':         {'id': None,    'name': 'NEW_NODE_ONLINE'},
        'priority':     {'id': None,    'name': 'Lower'},
        'nickName':     _this_nickname,
        'isHardCoded':  False,
        'data':         [nickname]
        }
    _message.send(vscp_msg)
    if not has_parent:
        step = 0.5 / PROBE_RETRIES_SHORT
        progress = 0.5
        _update_scan_progress(progress)
    for _ in range(PROBE_RETRIES_SHORT):
        check = False
        await asyncio.sleep(PROBE_SLEEP)
        while _message.available() > 0:
            vscp_result = _message.pop_front()
            # pylint: disable=unsubscriptable-object
            check = (   (vscp_result['class']['name'] == vscp_msg['class']['name'])
                    and (vscp_result['type']['name'] == 'PROBE_ACK')
                    )
            if check is True:
                result = vscp_result['nickName']
                _message.flush()
                break
            # pylint: enable=unsubscriptable-object
        if not has_parent:
            progress = progress + step
            _update_scan_progress(progress)
        if check is True:
            break
    if not has_parent:
        _async_work = False
        _message.disable_feeder(True)
        _update_scan_progress(1.0)
    return result


async def get_node_info(nickname: int) -> dict: # pylint: disable=too-many-branches, too-many-locals
    global _async_work # pylint: disable=global-statement
    has_parent = _async_work
    if _async_work is False:
        _async_work = True
        _message.enable_feeder()
        _update_scan_progress(0.0)
    vscp_msg = {
        'class':        {'id': None,    'name': 'CLASS1.PROTOCOL'},
        'type':         {'id': None,    'name': 'WHO_IS_THERE'},
        'priority':     {'id': None,    'name': 'Lower'},
        'nickName':     _this_nickname,
        'isHardCoded':  False,
        'data':         [nickname]
        }
    _message.send(vscp_msg)
    if not has_parent:
        step = 0.5 / PROBE_RETRIES_SHORT
        progress = 0.5
        _update_scan_progress(progress)
    max_response_messages = 7
    temp_result = {}
    guid = []
    mdf = []
    all_data_received = False
    is_hardcoded = False
    for _ in range(PROBE_RETRIES_LONG):
        await asyncio.sleep(PROBE_SLEEP)
        while _message.available() > 0:
            # pylint: disable=unsubscriptable-object
            vscp_result = _message.pop_front()
            check = (   (vscp_result['class']['name'] == vscp_msg['class']['name'])
                    and (vscp_result['type']['name'] == 'WHO_IS_THERE_RESPONSE')
                    and (vscp_result['nickName'] == nickname)
                    )
            if check is True:
                is_hardcoded = vscp_result['isHardCoded']
                try:
                    temp_result[int(vscp_result['data'][0])] = vscp_result['data'][1:]
                except (ValueError, TypeError):
                    pass
                all_data_received = len(temp_result) == max_response_messages
            # pylint: enable=unsubscriptable-object
            if all_data_received is True:
                break
        if not has_parent:
            progress = progress + step
            _update_scan_progress(progress)
        if all_data_received is True:
            break
    if all_data_received is True:
        result = []
        for idx in range(max_response_messages):
            result += temp_result[idx]
        guid = result[:16]
        mdf = result[16:]
        try:
            endpoint_idx = mdf.index(0)
        except ValueError:
            endpoint_idx = len(mdf)
        mdf = bytes(mdf[:endpoint_idx]).decode()
    if not has_parent:
        _async_work = False
        _message.disable_feeder(True)
        _update_scan_progress(1.0)
    return {'id': nickname, 'isHardCoded': is_hardcoded, 'guid': {'val': guid, 'str': guid_str(guid)}, 'mdf': mdf} if all_data_received else {}


async def scan(min_node_id: int = 0, max_node_id: int = MAX_NICKNAME_ID) -> int:
    global _async_work # pylint: disable=global-statement
    progress = 0.0
    _update_scan_progress(progress)
    result = -1
    if _async_work is False:
        _async_work = True
        _message.enable_feeder()
        _nodes.clear()
        min_node_id = max(min_node_id, 0)
        if max_node_id < min_node_id:
            max_node_id = min_node_id + 1
        max_node_id = min(max_node_id, MAX_NICKNAME_ID)
        step = 0.5 / (max_node_id - min_node_id + 1)
        for idx in range(min_node_id, max_node_id + 1):
            if idx is not _this_nickname:
                nickname = await probe_node(idx)
                if nickname is not None and is_node_on_list(nickname) is False:
                    _nodes.append({'id': nickname})
            progress = progress + step
            _update_scan_progress(progress)
        result = len(_nodes)
        if result > 0:
            step = 0.5 / result
            for idx, node in enumerate(_nodes):
                _nodes[idx] = await get_node_info(node['id'])
                progress = progress + step
                _update_scan_progress(progress)
        _message.disable_feeder(True)
        _async_work = False
    _update_scan_progress(1.0)
    return result


async def send_host_datetime():
    system_lag_fix_us = -5000
    global _async_work # pylint: disable=global-statement
    _update_scan_progress(0.0)
    if _async_work is False:
        _async_work = True
        vscp_msg = {
            'class':        {'id': None,    'name': 'CLASS1.INFORMATION'},
            'type':         {'id': None,    'name': 'DATETIME'},
            'priority':     {'id': None,    'name': 'Highest'},
            'nickName':     _this_nickname,
            'isHardCoded':  False
            }
        _update_scan_progress(0.5)
        now = datetime.datetime.now()
        wait_time = float((1 - ((now.time().microsecond + system_lag_fix_us) / 1000000.0)))
        now = now + datetime.timedelta(seconds=1)
        date =  (now.year   & 0x0FFF)   << 26       # 12 bits
        date |= (now.month  & 0x0F)     << 22       #  4 bits
        date |= (now.day    & 0x1F)     << 17       #  5 bits
        date |= (now.hour   & 0x1F)     << 12       #  5 bits
        date |= (now.minute & 0x3F)     << 6        #  6 bits
        date |= (now.second & 0x3F)     << 0        #  6 bits
        date &= 0x0000003FFFFFFFFF                  # 38 bits
        vscp_msg['data'] = [0x00, 0xFF, 0xFF] + list(date.to_bytes(5, 'big'))
        if wait_time < 0.1:
            time.sleep(wait_time)
        else:
            await asyncio.sleep(wait_time)
        _message.send(vscp_msg)
        _async_work = False
    _update_scan_progress(1.0)


async def set_nickname(old_nickname: int, new_nickname: int) -> bool:
    global _async_work # pylint: disable=global-statement
    progress = 0.0
    _update_scan_progress(progress)
    result = False
    if _async_work is False:
        _async_work = True
        progress = 0.5
        _update_scan_progress(progress)
        _message.enable_feeder()
        vscp_msg = {
            'class':        {'id': None,    'name': 'CLASS1.PROTOCOL'},
            'type':         {'id': None,    'name': 'SET_NICKNAME'},
            'priority':     {'id': None,    'name': 'Lower'},
            'nickName':     _this_nickname,
            'isHardCoded':  False,
            'data':         [old_nickname, new_nickname]
            }
        _message.send(vscp_msg)
        step = 0.5 / PROBE_RETRIES_LONG
        for _ in range(PROBE_RETRIES_LONG):
            await asyncio.sleep(PROBE_SLEEP)
            while _message.available() > 0:
                vscp_result = _message.pop_front()
                # pylint: disable=unsubscriptable-object
                result =    ((vscp_result['class']['name'] == vscp_msg['class']['name'])
                              and (vscp_result['type']['name'] == 'NICKNAME_ACCEPTED')
                              and (vscp_result['nickName'] == new_nickname)
                            )
                # pylint: enable=unsubscriptable-object
                if result is True:
                    break
            if result is True:
                break
            progress = progress + step
            _update_scan_progress(progress)
        _message.disable_feeder(True)
        _async_work = False
    _update_scan_progress(1.0)
    return result


async def extended_page_write_register(nickname: int, page: int, register_id: int, reg_vals: list) -> bool: # TODO add progress
    global _async_work # pylint: disable=global-statement
    result = False
    if _async_work is False: # pylint: disable=too-many-nested-blocks
        _async_work = True
        _message.enable_feeder()
        reg_vals = [numb for numb in reg_vals if isinstance(numb, int) and 0 <= numb <= 0xFF][:4]
        check = (   (max(min(0xFFFF, page), 0) == page)
                and (max(min(0xFF, register_id), 0) == register_id)
                )
        if check is True:
            vscp_msg = {
                'class':        {'id': None,    'name': 'CLASS1.PROTOCOL'},
                'type':         {'id': None,    'name': 'EXTENDED_PAGE_WRITE'},
                'priority':     {'id': None,    'name': 'Lower'},
                'nickName':     _this_nickname,
                'isHardCoded':  False,
                'data':         [nickname] + list(page.to_bytes(2, 'big')) + [register_id] + reg_vals
                }
            _message.send(vscp_msg)
            for _ in range(PROBE_RETRIES_LONG):
                await asyncio.sleep(PROBE_SLEEP)
                while _message.available() > 0:
                    # pylint: disable=unsubscriptable-object
                    vscp_result = _message.pop_front()
                    try:
                        check = (   (vscp_result['class']['name'] == vscp_msg['class']['name'])
                                and (vscp_result['type']['name'] == 'EXTENDED_PAGE_RESPONSE')
                                and (vscp_result['nickName'] == nickname)
                                and (page == int.from_bytes(bytes(vscp_result['data'][1:3]), 'big'))
                                )
                    except (ValueError, TypeError):
                        check = False
                    if check is True:
                        try:
                            temp_result = vscp_result['data'][4:]
                        except (ValueError, TypeError):
                            temp_result = []
                        result = reg_vals == temp_result
                        break
                    # pylint: enable=unsubscriptable-object
                if check is True:
                    break
        _message.disable_feeder(True)
        _async_work = False
    return result


# TODO add progress
async def extended_page_read_register(nickname: int, page: int, register_id: int, number_of_regs: int = None) -> list: # pylint: disable=too-many-branches
    global _async_work # pylint: disable=global-statement
    has_parent = _async_work
    if _async_work is False:
        _async_work = True
        _message.enable_feeder()
    result = None
    check = (   (max(min(0xFFFF, page), 0) == page)
            and (max(min(0xFF, register_id), 0) == register_id)
            and (number_of_regs is None
                 or (number_of_regs is not None and (max(min(0xFF, number_of_regs), 0) == number_of_regs))
                )
            )
    if check is True:
        vscp_msg = {
            'class':        {'id': None,    'name': 'CLASS1.PROTOCOL'},
            'type':         {'id': None,    'name': 'EXTENDED_PAGE_READ'},
            'priority':     {'id': None,    'name': 'Lower'},
            'nickName':     _this_nickname,
            'isHardCoded':  False,
            'data':         [nickname] + list(page.to_bytes(2, 'big')) + [register_id]
            }
        max_response_messages = 1
        if number_of_regs is not None:
            number_of_regs = int(min((0x100 - register_id), number_of_regs if 0 != number_of_regs else 0x100))
            max_response_messages = int(((number_of_regs - 1) / 4) + 1) if 0 != number_of_regs else 0x40
            vscp_msg['data'] += [number_of_regs]
        _message.send(vscp_msg)
        temp_result = {}
        all_data_received = False
        for _ in range(PROBE_RETRIES_LONG):
            await asyncio.sleep(PROBE_SLEEP)
            while _message.available() > 0:
                # pylint: disable=unsubscriptable-object
                vscp_result = _message.pop_front()
                try:
                    check = (   (vscp_result['class']['name'] == vscp_msg['class']['name'])
                            and (vscp_result['type']['name'] == 'EXTENDED_PAGE_RESPONSE')
                            and (vscp_result['nickName'] == nickname)
                            and (page == int.from_bytes(bytes(vscp_result['data'][1:3]), 'big'))
                            )
                except (ValueError, TypeError):
                    check = False
                if check is True:
                    try:
                        temp_result[int(vscp_result['data'][0])] = vscp_result['data'][4:]
                    except (ValueError, TypeError):
                        pass
                    all_data_received = len(temp_result) == max_response_messages
                # pylint: enable=unsubscriptable-object
                if all_data_received is True:
                    break
            if all_data_received is True:
                break
        if all_data_received is True:
            result = []
            for idx in range(max_response_messages):
                result += temp_result[idx]
    if not has_parent:
        _async_work = False
        _message.disable_feeder(True)
    return result


async def _firmware_enter_bootloader_mode(nickname: int, bootloader_type: int) -> dict:
    result = None
    try:
        credentials = await extended_page_read_register(nickname, 0x00, 0x92, 2)
        reg_0x92 = credentials[0]
        reg_0x93 = credentials[1]
        credentials = await extended_page_read_register(nickname, 0x00, 0xD0, 8)
        vscp_msg = {
            'class':        {'id': None,    'name': 'CLASS1.PROTOCOL'},
            'type':         {'id': None,    'name': 'ENTER_BOOT_LOADER'},
            'priority':     {'id': None,    'name': 'Lowest'},
            'nickName':     _this_nickname,
            'isHardCoded':  False,
            'data':         [nickname,          bootloader_type,    credentials[0], credentials[3],
                             credentials[5],    credentials[7],     reg_0x92,       reg_0x93
                            ]
            }
        _message.send(vscp_msg)
        stop = False
        for _ in range(PROBE_RETRIES_LONG):
            await asyncio.sleep(PROBE_SLEEP)
            while _message.available() > 0:
                # pylint: disable=unsubscriptable-object
                vscp_result = _message.pop_front()
                check = (   (vscp_result['class']['name'] == vscp_msg['class']['name'])
                        and (vscp_result['nickName'] == nickname)
                        )
                if check is True:
                    match vscp_result['type']['name']:
                        case 'ACK_BOOT_LOADER':
                            try:
                                flash_block_size = int.from_bytes(bytes(vscp_result['data'][:4]), 'big')
                                number_of_blocks = int.from_bytes(bytes(vscp_result['data'][-4:]), 'big')
                                result = (flash_block_size, number_of_blocks)
                            except ValueError:
                                pass
                            stop = True
                        case 'NACK_BOOT_LOADER':
                            stop = True
                        case _:
                            pass
                    break
                # pylint: enable=unsubscriptable-object
            if stop is True:
                _message.flush()
                break
    except (ValueError, TypeError):
        pass
    return result


async def _firmware_send_start_data_block(nickname: int, block_id: int) -> bool:
    result = False
    vscp_msg = {
        'class':        {'id': None,    'name': 'CLASS1.PROTOCOL'},
        'type':         {'id': None,    'name': 'START_BLOCK'},
        'priority':     {'id': None,    'name': 'Lowest'},
        'nickName':     _this_nickname,
        'isHardCoded':  False,
        'data':         list(block_id.to_bytes(4, 'big'))
        }
    _message.send(vscp_msg)
    stop = False
    for _ in range(PROBE_RETRIES_LONG):
        await asyncio.sleep(PROBE_SLEEP)
        while _message.available() > 0:
            # pylint: disable=unsubscriptable-object
            vscp_result = _message.pop_front()
            check = (   (vscp_result['class']['name'] == vscp_msg['class']['name'])
                    and (vscp_result['nickName'] == nickname)
                    )
            if check is True:
                match vscp_result['type']['name']:
                    case 'START_BLOCK_ACK':
                        result = True
                        stop = True
                    case 'START_BLOCK_NACK':
                        stop = True
                    case _:
                        pass
                if stop is True:
                    break
            # pylint: enable=unsubscriptable-object
        if stop is True:
            _message.flush()
            break
    return result


async def _firmware_send_data_chunk(nickname: int, chunk_gap: int, chunk: list) -> bool:
    result = False
    vscp_msg = {
        'class':        {'id': None,    'name': 'CLASS1.PROTOCOL'},
        'type':         {'id': None,    'name': 'BLOCK_DATA'},
        'priority':     {'id': None,    'name': 'Lowest'},
        'nickName':     _this_nickname,
        'isHardCoded':  False,
        }
    await asyncio.sleep(chunk_gap)
    vscp_msg['data'] = chunk
    retry = 0
    while retry < FIRMWARE_CHUNK_WRITE_RETRIES:
        norepeat = False
        retry += 1
        _message.send(vscp_msg)
        for idx in range(PROBE_RETRIES_SHORT):
            norepeat = (idx + 1) >= PROBE_RETRIES_SHORT
            stop = False
            while _message.available() > 0:
                # pylint: disable=unsubscriptable-object
                vscp_result = _message.pop_front()
                check = (   (vscp_result['class']['name'] == 'CLASS1.PROTOCOL')
                        and (vscp_result['nickName'] == nickname)
                        )
                if check is True:
                    match vscp_result['type']['name']:
                        case 'BLOCK_CHUNK_ACK':
                            norepeat = True
                            stop = True
                        case 'BLOCK_CHUNK_NACK':
                            stop = True
                        case _:
                            pass
                if stop is True:
                    break
            # pylint: enable=unsubscriptable-object
            if stop is True:
                break
            await asyncio.sleep(PROBE_SLEEP)
        if norepeat is True:
            result = True
            retry = FIRMWARE_CHUNK_WRITE_RETRIES
    return result


async def _firmware_send_data_block(nickname: int, chunk_gap: int, block: list, progress: float, progress_chunk: float) -> bool: # pylint: disable=too-many-locals
    result = False
    block_crc = Calculator(Crc16.IBM_3740, True).checksum(bytes(block))
    chunks = int(len(block) / MAX_CAN_DLC)
    step = progress_chunk / chunks
    block_progress = progress
    for chunk in [block[i:i + MAX_CAN_DLC] for i in range(0, len(block), MAX_CAN_DLC)]:
        result = await _firmware_send_data_chunk(nickname, chunk_gap, chunk)
        if result is False:
            break
        block_progress = block_progress + step
        _update_scan_progress(block_progress)
    if result is True:
        stop = False
        result = False
        for _ in range(PROBE_RETRIES_LONG):
            await asyncio.sleep(PROBE_SLEEP)
            while _message.available() > 0:
                # pylint: disable=unsubscriptable-object
                vscp_result = _message.pop_front()
                check = (   (vscp_result['class']['name'] == 'CLASS1.PROTOCOL')
                        and (vscp_result['nickName'] == nickname)
                        )
                if check is True:
                    match vscp_result['type']['name']:
                        case 'BLOCK_DATA_ACK':
                            try:
                                received_crc = int.from_bytes(bytes(vscp_result['data'][:2]), 'big')
                            except ValueError:
                                received_crc = None
                            if isinstance(received_crc, int) and received_crc == block_crc:
                                result = True
                            stop = True
                        case 'BLOCK_DATA_NACK':
                            stop = True
                        case _:
                            pass
                # pylint: enable=unsubscriptable-object
            if stop is True:
                _message.flush()
                break
    return result


async def _firmware_send_program_data_block(nickname: int, block_id: int) -> bool:
    result = False
    vscp_msg = {
        'class':        {'id': None,    'name': 'CLASS1.PROTOCOL'},
        'type':         {'id': None,    'name': 'PROGRAM_BLOCK_DATA'},
        'priority':     {'id': None,    'name': 'Lowest'},
        'nickName':     _this_nickname,
        'isHardCoded':  False,
        'data':         list(block_id.to_bytes(4, 'big'))
        }
    _message.send(vscp_msg)
    stop = False
    for _ in range(FIRMWARE_WRITE_ACK_CHECK_RETRIES):
        await asyncio.sleep(PROBE_SLEEP)
        while _message.available() > 0:
            # pylint: disable=unsubscriptable-object
            vscp_result = _message.pop_front()
            check = (   (vscp_result['class']['name'] == vscp_msg['class']['name'])
                    and (vscp_result['nickName'] == nickname)
                    )
            if check is True:
                match vscp_result['type']['name']:
                    case 'PROGRAM_BLOCK_DATA_ACK':
                        try:
                            if int.from_bytes(bytes(vscp_result['data'][:4]), 'big') == block_id:
                                result = True
                                stop = True
                        except ValueError:
                            pass
                    case 'PROGRAM_BLOCK_DATA_NACK':
                        if int.from_bytes(bytes(vscp_result['data'][1:5]), 'big') == block_id:
                            stop = True
                    case _:
                        pass
            # pylint: enable=unsubscriptable-object
            if stop is True:
                break
        if stop is True:
            _message.flush()
            break
    return result


async def _firmware_activate_new_image(nickname: int, firmware_crc: int) -> bool:
    result = False
    vscp_msg = {
        'class':        {'id': None,    'name': 'CLASS1.PROTOCOL'},
        'type':         {'id': None,    'name': 'ACTIVATE_NEW_IMAGE'},
        'priority':     {'id': None,    'name': 'Lowest'},
        'nickName':     _this_nickname,
        'isHardCoded':  False,
        'data':         list(firmware_crc.to_bytes(2, 'big'))
        }
    _message.send(vscp_msg)
    stop = False
    for _ in range(FIRMWARE_WRITE_ACK_CHECK_RETRIES):
        await asyncio.sleep(PROBE_SLEEP)
        while _message.available() > 0:
            # pylint: disable=unsubscriptable-object
            vscp_result = _message.pop_front()
            check = (   (vscp_result['class']['name'] == vscp_msg['class']['name'])
                    and (vscp_result['nickName'] == nickname)
                    )
            if check is True:
                match vscp_result['type']['name']:
                    case 'ACTIVATE_NEW_IMAGE_ACK':
                        result = True
                        stop = True
                    case 'ACTIVATE_NEW_IMAGE_NACK':
                        stop = True
                    case 'NEW_NODE_ONLINE':
                        try:
                            if vscp_result['data'][0] == nickname:
                                result = True
                        except TypeError:
                            pass
                        stop = True
                    case _:
                        pass
            # pylint: enable=unsubscriptable-object
            if stop is True:
                break
        if stop is True:
            _message.flush()
            break
    return result


async def firmware_upload(nickname: int, firmware: list) -> bool: # pylint: disable=too-many-locals
    global _async_work # pylint: disable=global-statement
    result = False
    progress = 0.0
    _update_scan_progress(progress)
    if _async_work is False: # pylint: disable=too-many-nested-blocks
        _async_work = True
        _message.enable_feeder()
        bootloader_type = 0x00
        device_block_params = await _firmware_enter_bootloader_mode(nickname, bootloader_type)
        progress = 0.02
        _update_scan_progress(progress)
        if device_block_params is not None:
            flash_block_size = device_block_params[0]
            number_of_blocks = device_block_params[1]
            block_gap = len(firmware) % flash_block_size
            if 0 != block_gap:
                firmware.extend(FIRMWARE_FLASH_ERASED_VALUE for _ in range(flash_block_size - block_gap))
            firmware_crc = Calculator(Crc16.IBM_3740, True).checksum(bytes(firmware))
            blocks_to_program = int(len(firmware) / flash_block_size)
            if blocks_to_program <= number_of_blocks:
                step = 0.96 / blocks_to_program
                success = False
                for idx, block in enumerate([firmware[i:i + flash_block_size] for i in range(0, len(firmware), flash_block_size)]):
                    retry = 0
                    while retry < FIRMWARE_BLOCK_WRITE_RETRIES:
                        chunk_gap = PROBE_SLEEP * (1 << retry)
                        retry += 1
                        success = await _firmware_send_start_data_block(nickname, idx)
                        if success is True:
                            success = await _firmware_send_data_block(nickname, chunk_gap, block, progress, step)
                        else:
                            await asyncio.sleep(BLOCK_WRITE_GAP)
                        if success is True:
                            success = await _firmware_send_program_data_block(nickname, idx)
                        if success is True:
                            break
                    progress = progress + step
                    _update_scan_progress(progress)
                    if success is False:
                        break #Fail to program firmware
                _update_scan_progress(0.98)
                if success is True:
                    result = await _firmware_activate_new_image(nickname, firmware_crc)
        _message.disable_feeder(True)
        _async_work = False
    _update_scan_progress(1.0)
    return result
