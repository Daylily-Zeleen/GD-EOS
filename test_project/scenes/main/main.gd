extends CanvasLayer


@export var product_name :String = ""
@export var product_version :String = ""
@export var product_id :String = ""
@export var sandbox_id :String = ""
@export var deployment_id :String = ""
@export var client_id :String = ""
@export var client_secret :String = ""
@export var encryption_key :String = ""

@onready var login_type_option_btn :OptionButton = %LoginTypeOptionBtn
@onready var external_type_option_btn :OptionButton = %ExternalTypeOptionBtn
@onready var id_line_edit :LineEdit = %IdLineEdit
@onready var token_line_edit :LineEdit = %TokenLineEdit
@onready var login_btn :Button = %LoginBtn


var _epic_account_id: EOSEpicAccountId
var _product_user_id: EOSProductUserId

func _init() -> void:
	# Initialize EOS
	var init_options := EOSInitializeOptions.new()
	init_options.product_name = _get_config(&"product_name")
	init_options.product_version = _get_config(&"product_version")
	var result_code: EOS.Result =  EOS.initialize(init_options)
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
	# Setup login type option button.
	for e in ClassDB.class_get_enum_constants(&"EOSAuth", &"LoginCredentialType"):
		login_type_option_btn.add_item(e.split("_", false, 1)[1])
		login_type_option_btn.set_item_metadata(login_type_option_btn.item_count - 1, EOSAuth[e])

	# Setup external type option button,
	for e in ClassDB.class_get_enum_constants(&"EOS", &"ExternalCredentialType"):
		external_type_option_btn.add_item(e.split("_", false, 1)[1])
		external_type_option_btn.set_item_metadata(external_type_option_btn.item_count - 1, EOS[e])

	login_btn.pressed.connect(_on_login_btn_pressed)


# ========================================================
func _on_login_btn_pressed() -> void:
	login_btn.disabled = true

	var auth_login_credentials := EOSAuth_Credentials.new()
	auth_login_credentials.type = login_type_option_btn.get_selected_metadata()
	auth_login_credentials.external_type = external_type_option_btn.get_selected_metadata()
	auth_login_credentials.id = id_line_edit.text
	auth_login_credentials.token = token_line_edit.text

	var auth_login_result :EOSAuth_LoginCallbackInfo = await EOSAuth.login(
		auth_login_credentials,
		EOSAuth.AS_BasicProfile | EOSAuth.AS_FriendsList | EOSAuth.AS_Presence,
		0)
	if auth_login_result.result_code != EOS.Success:
		printerr("== Login Fail: ", EOS.result_to_string(auth_login_result.result_code))
		login_btn.disabled = false
		return

	# NOTE: After workflow only tested when credentials type is AccountPortal or Developer.
	_epic_account_id = auth_login_result.local_user_id

	var copy_token_result := EOSAuth.copy_id_token(_epic_account_id)
	if copy_token_result.result_code != EOS.Success:
		printerr("== Copy token failed: ", EOS.result_to_string(copy_token_result.result_code))
		return

	var connect_login_credentials := EOSConnect_Credentials.new()
	connect_login_credentials.type = EOS.ECT_EPIC_ID_TOKEN
	connect_login_credentials.token = copy_token_result.id_token.json_web_token

	var user_login_info := EOSConnect_UserLoginInfo.new()

	var connect_login_result :EOSConnect_LoginCallbackInfo = await EOSConnect.login(connect_login_credentials, user_login_info)
	if connect_login_result.result_code == EOS.InvalidUser:
		print("This epic account has not Product User id, creating for it.")
		# This token has not product user id, so, create it.
		var create_result :EOSConnect_CreateUserCallbackInfo = await EOSConnect.create_user(connect_login_result.continuance_token)
		if create_result.result_code != EOS.Success:
			printerr("=== Create User failed: ", EOS.result_to_string(create_result.result_code))
			return
		else:
			_product_user_id = create_result.local_user_id
			print("Create User success, product user id: ", _product_user_id)
	elif connect_login_result.result_code != EOS.Success:
		printerr("== Connect login failed: ", EOS.result_to_string(connect_login_result.result_code))
		return
	else:
		_product_user_id = connect_login_result.local_user_id
	print("=== Connect login success: ", _product_user_id)

	%LoginUI.hide()

# ========================================================
func _get_config(key:StringName) -> String:
	const cfg_file :String = "res://.env"
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


static func _eos_log_callback(category:String, message: String, level: EOS.LogLevel) -> void:
	var msg :String = "[%s]: %s" % [category, message]
	if level >= EOS.LOG_Info:
		print(msg)
	elif level >= EOS.LOG_Warning:
		print_rich("[color=yellow]%s[/color]" % msg)
	elif level >= EOS.LOG_Error:
		print_rich("[color=orange]%s[/color]" % msg)
	else:
		printerr(msg)
