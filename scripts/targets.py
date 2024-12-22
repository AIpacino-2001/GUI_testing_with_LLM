
setup_scripts = {
    'commons': '../benchmark/Themis/commons/login-2.11.0-#3244.py',
    'collect': './setup_script/collect_start_demo.py',
    'MaterialFB': './setup_script/materialFB.py',
    'infinity-for-reddit': './setup_script/reddit.py',
}

def get_initial_knowledge(app_id, persona_name, app_name):
    _initial_knowledge_map = {
        'AnkiDroid': [f'{persona_name} owns an existing account on AnkiWeb', f'{persona_name} started the {app_name} app'],


    }
    if app_id in _initial_knowledge_map:
        return _initial_knowledge_map[app_id]
    else:
        return [f'{persona_name} started the {app_name} app']


initial_knowledge_map = lambda app_id, persona_name, app_name: get_initial_knowledge(app_id, persona_name, app_name)
