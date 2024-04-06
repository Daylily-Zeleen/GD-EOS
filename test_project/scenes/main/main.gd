# NOTE: Only tested when credentials type is AccountPortal or Developer.
extends Node

# EOS settings:
@export var product_name: String = ""
@export var product_version: String = ""
@export var product_id: String = ""
@export var sandbox_id: String = ""
@export var deployment_id: String = ""
@export var client_id: String = ""
@export var client_secret: String = ""
@export var encryption_key: String = ""

@onready var login_type_option_btn: OptionButton = %LoginTypeOptionBtn
@onready var external_type_option_btn: OptionButton = %ExternalTypeOptionBtn
@onready var id_line_edit: LineEdit = %IdLineEdit
@onready var token_line_edit: LineEdit = %TokenLineEdit
@onready var login_btn: Button = %LoginBtn

@onready var lobbies_item_list: ItemList = %LobbiesItemList

var _epic_account_id: EOSEpicAccountId
var _product_user_id: EOSProductUserId
var _entered_lobby_id: String


func _init() -> void:
	# Initialize EOS
	var init_options := EOSInitializeOptions.new()
	init_options.product_name = _get_config(&"product_name")
	init_options.product_version = _get_config(&"product_version")
	var result_code: EOS.Result = EOS.initialize(init_options)
	if result_code != EOS.Success:
		printerr("Initialize EOS faild: ", EOS.result_to_string(result_code))
		return

	# Setup Logging.
	EOS.set_logging_callback(_eos_log_callback)
	EOS.set_log_level(EOS.LC_ALL_CATEGORIES, EOS.LOG_Info)

	# Create platform
	var create_options := EOSPlatform_Options.new()
	create_options.product_id = _get_config(&"product_id")
	create_options.sandbox_id = _get_config(&"sandbox_id")
	create_options.deployment_id = _get_config(&"deployment_id")
	create_options.client_credentials = EOSPlatform_ClientCredentials.new()
	create_options.client_credentials.client_id = _get_config(&"client_id")
	create_options.client_credentials.client_secret = _get_config(&"client_secret")
	create_options.encryption_key = _get_config(&"encryption_key")
	create_options.flags = EOSPlatform.PF_DISABLE_OVERLAY
	EOSPlatform.platform_create(create_options)


func _ready() -> void:
	# Try to set windows position
	for i in range(2):
		if not OS.has_feature("instance_%d" % i):
			continue
		get_tree().root.position = Vector2(0, 30) if i == 0 else get_tree().root.size * 0.6

	# Setup login type option button.
	for e in ClassDB.class_get_enum_constants(&"EOSAuth", &"LoginCredentialType"):
		login_type_option_btn.add_item(e.split("_", false, 1)[1])
		login_type_option_btn.set_item_metadata(login_type_option_btn.item_count - 1, EOSAuth[e])

	# Setup external type option button,
	for e in ClassDB.class_get_enum_constants(&"EOS", &"ExternalCredentialType"):
		external_type_option_btn.add_item(e.split("_", false, 1)[1])
		external_type_option_btn.set_item_metadata(external_type_option_btn.item_count - 1, EOS[e])

	login_btn.pressed.connect(_on_login_btn_pressed)

	#
	%CreateBtn.pressed.connect(_create_lobby_async)
	%RefreshBtn.pressed.connect(_refresh_lobbies_list_async)
	%JoinBtn.pressed.connect(_join_lobbies_async)


func _exit_tree() -> void:
	if _entered_lobby_id and EOSLobby.copy_lobby_details(_entered_lobby_id, _product_user_id).lobby_details.get_lobby_owner() == _product_user_id:
		EOSLobby.destroy_lobby(_product_user_id, _entered_lobby_id)


# ========================================================
func _on_login_btn_pressed() -> void:
	login_btn.disabled = true

	# Auth login
	var auth_login_credentials := EOSAuth_Credentials.new()
	auth_login_credentials.type = login_type_option_btn.get_selected_metadata()
	auth_login_credentials.external_type = external_type_option_btn.get_selected_metadata()
	auth_login_credentials.id = id_line_edit.text
	auth_login_credentials.token = token_line_edit.text

	var auth_login_result: EOSAuth_LoginCallbackInfo = await EOSAuth.login(auth_login_credentials, EOSAuth.AS_BasicProfile | EOSAuth.AS_FriendsList | EOSAuth.AS_Presence, 0)
	if auth_login_result.result_code != EOS.Success:
		printerr("== Login Fail: ", EOS.result_to_string(auth_login_result.result_code))
		login_btn.disabled = false
		return

	_epic_account_id = auth_login_result.local_user_id

	# Copy id token
	var copy_token_result := EOSAuth.copy_id_token(_epic_account_id)
	if copy_token_result.result_code != EOS.Success:
		printerr("== Copy token failed: ", EOS.result_to_string(copy_token_result.result_code))
		await _auth_logout_async()
		return

	var connect_login_credentials := EOSConnect_Credentials.new()
	connect_login_credentials.type = EOS.ECT_EPIC_ID_TOKEN
	connect_login_credentials.token = copy_token_result.id_token.json_web_token

	var user_login_info := EOSConnect_UserLoginInfo.new()

	# Connect login
	var connect_login_result: EOSConnect_LoginCallbackInfo = await EOSConnect.login(connect_login_credentials, user_login_info)
	if connect_login_result.result_code == EOS.InvalidUser:
		print("This epic account has not Product User id, creating for it.")
		# This token has not product user id, so, create it.
		var create_result: EOSConnect_CreateUserCallbackInfo = await EOSConnect.create_user(connect_login_result.continuance_token)
		if create_result.result_code != EOS.Success:
			printerr("=== Create User failed: ", EOS.result_to_string(create_result.result_code))
			await _auth_logout_async()
			return
		else:
			_product_user_id = create_result.local_user_id
			print("Create User success, product user id: ", _product_user_id)
	elif connect_login_result.result_code != EOS.Success:
		printerr("== Connect login failed: ", EOS.result_to_string(connect_login_result.result_code))
		await _auth_logout_async()
		return
	else:
		_product_user_id = connect_login_result.local_user_id
	print("=== Connect login success: ", _product_user_id)

	%LoginUI.hide()
	%LobbyUI.show()


func _auth_logout_async() -> void:
	var logout_result: EOSAuth_LogoutCallbackInfo = await EOSAuth.logout(_epic_account_id)
	_epic_account_id = null
	login_btn.disabled = false
	if logout_result.result_code != EOS.Success:
		printerr("== Auth logout failed: ", EOS.result_to_string(logout_result.result_code))
	else:
		print("Auth logout success: ", logout_result.local_user_id)


func _create_lobby_async() -> void:
	var lobby_id_to_create := %LobbyNameLineEdit.text as String
	if lobby_id_to_create.is_empty():
		printerr("== Please enter a lobby name brfore create.")
		return
	set_lobby_btns_disabled(true)
	var create_options := EOSLobby_CreateLobbyOptions.new()
	create_options.lobby_id = lobby_id_to_create
	create_options.local_user_id = _product_user_id
	create_options.max_lobby_members = 2
	create_options.bucket_id = "TestBucket"
	var create_result: EOSLobby_CreateLobbyCallbackInfo = await EOSLobby.create_lobby(create_options)
	if create_result.result_code != EOS.Success:
		printerr("== Create lobby failed: ", EOS.result_to_string(create_result.result_code))
		set_lobby_btns_disabled(false)
		return

	_entered_lobby_id = create_result.lobby_id

	# Initialize lobby info, we use "started" to sreach lobbies.
	var ulmr := EOSLobby.update_lobby_modification(_product_user_id, _entered_lobby_id)
	if ulmr.result_code != EOS.Success:
		printerr("== Update lobby modification failed: ", EOS.result_to_string(ulmr.result_code))
		set_lobby_btns_disabled(false)
		return
	var lobby_modification := ulmr.lobby_modification

	var parameter := EOSLobby_AttributeData.new()
	parameter.key = "started"
	parameter.value = false
	var add_attribute_result = lobby_modification.add_attribute(parameter, EOSLobby.LAT_PUBLIC)
	if add_attribute_result != EOS.Success:
		printerr("== Update lobby modification failed: ", EOS.result_to_string(create_result.result_code))
		set_lobby_btns_disabled(false)
		return

	var update_result: EOSLobby_UpdateLobbyCallbackInfo = await EOSLobby.update_lobby(lobby_modification)
	if update_result.result_code != EOS.Success:
		printerr("== Update lobby failed: ", EOS.result_to_string(update_result.result_code))
		set_lobby_btns_disabled(false)
		return
	print("===== Create lobby success =====")
	_start_game()


func _refresh_lobbies_list_async() -> void:
	set_lobby_btns_disabled(true)
	var clsr := EOSLobby.create_lobby_search(10)
	if clsr.result_code != EOS.Success:
		printerr("== Create loggby search failed: ", EOS.result_to_string(clsr.result_code))
		set_lobby_btns_disabled(false)
		return
	var lobby_search: EOSLobbySearch = clsr.lobby_search
	# Ignore strated lobbies.
	var parameter := EOSLobby_AttributeData.new()
	parameter.key = "started"
	parameter.value = false
	lobby_search.set_parameter(parameter, EOS.CO_EQUAL)

	var find_result_code: EOS.Result = await lobby_search.find(_product_user_id)
	if find_result_code != EOS.Success:
		printerr("== Find lobbies failed: ", EOS.result_to_string(find_result_code))
		set_lobby_btns_disabled(false)
		return

	lobbies_item_list.clear()
	for i in range(lobby_search.get_search_result_count()):
		var csr: LobbySearch_CopySearchResultByIndexResult = lobby_search.copy_search_result_by_index(i)
		if csr.result_code != EOS.Success:
			printerr("== Copy lobby search result failed: ", EOS.result_to_string(csr.result_code))
			continue
		var lobby_detials: EOSLobbyDetails = csr.lobby_details
		var cir := lobby_detials.copy_info()
		if cir.result_code != EOS.Success:
			printerr("== Copy lobby details info failed: ", EOS.result_to_string(cir.result_code))
			continue
		var info: EOSLobbyDetails_Info = cir.lobby_details_info
		lobbies_item_list.add_item("%s - %d/%d" % [info.lobby_id, lobby_detials.get_member_count(), info.max_members])
		lobbies_item_list.set_item_metadata(lobbies_item_list.item_count - 1, lobby_detials)
	set_lobby_btns_disabled(false)
	print("===== Refresh lobbies list success =====")


func _join_lobbies_async() -> void:
	var selected := lobbies_item_list.get_selected_items()
	if selected.size() != 1:
		printerr("== Please select a lobby befor joining.")
		return

	var lobby_details: EOSLobbyDetails = lobbies_item_list.get_item_metadata(selected[0])
	assert(lobby_details)
	set_lobby_btns_disabled(true)
	var join_lobby_options := EOSLobby_JoinLobbyOptions.new()
	join_lobby_options.lobby_details = lobby_details
	join_lobby_options.local_user_id = _product_user_id
	var join_result: EOSLobby_JoinLobbyCallbackInfo = await EOSLobby.join_lobby(join_lobby_options)

	if join_result.result_code != EOS.Success:
		printerr("== Join lobby failed: ", EOS.result_to_string(join_result.result_code))
		set_lobby_btns_disabled(false)
		return

	lobbies_item_list.clear()
	_entered_lobby_id = join_result.lobby_id
	print("===== Join Lobby success =====")
	_start_game()


# ========================================================
func _start_game() -> void:
	%LobbyUI.hide()
	%UI.hide()
	%Players.setup_local(_product_user_id, _entered_lobby_id)


func set_lobby_btns_disabled(disabled: bool) -> void:
	%RefreshBtn.disabled = disabled
	%CreateBtn.disabled = disabled
	%JoinBtn.disabled = disabled
	(%LobbyNameLineEdit as LineEdit).editable = not disabled


func _get_config(key: StringName) -> String:
	const cfg_file: String = "res://.env"
	if not FileAccess.file_exists(cfg_file):
		return get(key)
	var cfg := ConfigFile.new() as ConfigFile
	if not cfg.load(cfg_file) == OK:
		return get(key)
	var config_key := key.to_upper()
	if not cfg.has_section_key("", config_key):
		printerr("Config has not key: ", config_key)
		return get(key)
	return cfg.get_value("", config_key)


static func _eos_log_callback(category: String, message: String, level: EOS.LogLevel) -> void:
	var msg: String = "[%s]: %s" % [category, message]
	if level >= EOS.LOG_Info:
		print(msg)
	elif level >= EOS.LOG_Warning:
		print_rich("[color=yellow]%s[/color]" % msg)
	elif level >= EOS.LOG_Error:
		print_rich("[color=orange]%s[/color]" % msg)
	else:
		printerr(msg)
