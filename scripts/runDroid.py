import logging
import androguard.core.axml
import androguard.core.apk
import time
import os
import json
from collections import OrderedDict
from droidbot.device import Device
from droidbot.app import App
from droidbot.input_event import KeyEvent
from GTestAgent import TaskBasedAgent
from device_manager import DeviceManager, ExternalAction, recover_activity_stack, is_loading_state
from scripts.targets import initial_knowledge_map

# 设置所有androguard相关模块的日志级别
logging.getLogger('androguard').setLevel(logging.ERROR)
logging.getLogger('androguard.core').setLevel(logging.ERROR)
logging.getLogger('androguard.core.axml').setLevel(logging.ERROR)
logging.getLogger('androguard.core.bytecodes').setLevel(logging.ERROR)
logging.getLogger('androguard.core.bytecodes.apk').setLevel(logging.ERROR)

# 设置其他模块的日志级别
logging.getLogger('droidbot').setLevel(logging.INFO)
logging.getLogger('GTestAgent').setLevel(logging.INFO)

# 如果还有其他debug信息，可以设置全局日志级别
logging.getLogger().setLevel(logging.WARNING)

# 设置androguard的日志级别为WARNING或更高
logging.getLogger('androguard').setLevel(logging.WARNING)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PERSONA_PATH = os.path.join(BASE_DIR, '..', 'resources/personas')
WAIT_TIME = 1
MAX_ACTIONS = 8000


def read_persona_file(profile_name):
    profile_file = os.path.join(PERSONA_PATH, f'{profile_name}.txt')
    if not os.path.exists(profile_file):
        raise FileNotFoundError(f'找不到角色配置文件: {profile_name}')

    with open(profile_file, 'r') as f:
        content = f.read().strip()

    result = OrderedDict()
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith('-'):
            line = line[1:].strip()
            key, value = [x.strip() for x in line.split(':')]
            result[key] = value

    return result


def execute_test(test_device, test_app, test_persona, debug_mode=False):
    test_start = time.time()
    print("\n[系统] 初始化测试环境...")

    test_agent = TaskBasedAgent(output_path, app=test_app, persona=test_persona, debug_mode=debug_mode)
    print(f"[系统] 测试代理初始化完成: {test_app.package_name}")

    device_ctrl = DeviceManager(test_device, test_app, output_dir=output_path)
    test_agent.set_current_gui_state(device_ctrl.current_state)

    need_update = False
    print("[系统] 开始执行自动化测试...\n")

    max_wait = 3
    wait_count = 0

    while True:
        if test_agent.step_count >= MAX_ACTIONS:
            print(f'\n[系统] 测试完成: 已达到最大步数 ({test_agent.step_count})')
            test_device.uninstall_app(test_app)
            test_device.disconnect()
            test_device.tear_down()
            exit(0)

        if test_agent.step_count % 10 == 0:
            remaining = round(((3600 - (time.time() - test_start)) / 60), 2)
            print(f'[进度] 剩余测试时间: {remaining} 分钟')

        if is_loading_state(device_ctrl.current_state):
            wait_count += 1
            if wait_count > max_wait:
                print('[警告] 页面响应超时，正在返回上一页...')
                back_event = KeyEvent(name='BACK')
                device_ctrl.send_event_to_device(back_event)
                test_agent.memory.append_to_working_memory(
                    ExternalAction('检测到页面无响应，执行返回操作', [{}]),
                    'ACTION'
                )
                wait_count = 0
                continue
            else:
                print('[等待] 页面加载中...')
                time.sleep(WAIT_TIME)
                device_ctrl.fetch_device_state()
                need_update = True
                continue

        if need_update:
            test_agent.set_current_gui_state(device_ctrl.current_state)
            device_ctrl.add_new_utg_edge()
            need_update = False

        action = test_agent.step()
        test_agent.save_memory_snapshot()

        if action:
            event_list = []
            events = action.to_droidbot_event()
            for event in events:
                event_dict = device_ctrl.send_event_to_device(
                    event,
                    capture_intermediate_state=True,
                    agent=test_agent
                )
                event_list.append(event_dict)

            action.add_event_records(event_list)
            recover_activity_stack(device_ctrl, test_agent)
            test_agent.set_current_gui_state(device_ctrl.current_state)


if __name__ == "__main__":
    print("==== 安卓应用测试工具 v1.0 ====")
    print(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # 硬编码配置
    app_name = "AnkiDroid"
    output_folder = "../evaluation/data_new/AnkiDroid"
    is_emulator = True
    profile = "ZhangSan"

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(BASE_DIR, output_folder, f"test_run_{timestamp}")

    print(f"\n[系统] 初始化设备连接...")
    android_device = Device(
        device_serial='emulator-5554',
        output_dir=output_path,
        grant_perm=True,
        is_emulator=is_emulator
    )
    android_device.set_up()
    android_device.connect()
    print("[系统] 设备连接成功!")

    print(f"\n[系统] 加载应用: {app_name}")
    app_file = os.path.join(BASE_DIR, '../target_apps', f'{app_name}.apk')
    target_app = App(app_file, output_dir=output_path)
    app_display_name = target_app.apk.get_app_name()

    print("\n[系统] 配置测试角色信息...")
    role_config = OrderedDict()
    role_config.update(read_persona_file(profile))
    role_config.update({
        'ultimate_goal': 'visit as many pages as possible while trying their core functionalities',
        'initial_knowledge': initial_knowledge_map(app_name, role_config['name'], app_display_name)
    })

    print("\n[系统] 创建输出目录...")
    os.makedirs(output_path, exist_ok=True)

    print("\n[系统] 保存实验配置...")
    with open(f'{output_path}/test_config.json', 'w', encoding='utf-8') as f:
        json.dump({
            'app_name': app_display_name,
            'app_path': os.path.abspath(app_file),
            'device_id': android_device.serial,
            'start_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'profile': profile
        }, f, indent=2, ensure_ascii=False)

    print("\n[系统] 开始执行测试...")
    execute_test(android_device, target_app, role_config)
