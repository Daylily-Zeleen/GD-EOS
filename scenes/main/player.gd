extends Sprite2D

const move_spped = 200.0
var _target_global_position: Vector2 = Vector2.ZERO
var _move_dir: Vector2 = Vector2.ZERO


func _ready() -> void:
	# Pass player node's authority by node name.
	var auth_peer_id := name.to_int()
	set_multiplayer_authority(auth_peer_id)

	# Only authority peer is local can enable input.
	var is_local := auth_peer_id == multiplayer.multiplayer_peer.get_unique_id()
	set_process_unhandled_input(is_local)

	position = get_tree().root.size * 0.5
	%IdLabel.text = str(auth_peer_id)


func _unhandled_input(event: InputEvent) -> void:
	for action in [&"ui_left", &"ui_right", &"ui_up", &"ui_down"]:
		if not event.is_action(action):
			continue

		_move_dir = Input.get_vector(&"ui_left", &"ui_right", &"ui_up", &"ui_down")
		_target_global_position = Vector2.ZERO

		get_tree().root.set_input_as_handled()
		return

	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT and event.is_released() and not event.is_echo():
			_target_global_position = event.global_position
			_move_dir = Vector2.ZERO
			get_tree().root.set_input_as_handled()


func _process(delta: float) -> void:
	if not _target_global_position.is_zero_approx() and not global_position.is_equal_approx(_target_global_position):
		var remain_distance := _target_global_position.distance_to(global_position)
		global_position += (_target_global_position - global_position).normalized() * move_spped * delta
		if _target_global_position.distance_to(global_position) >= remain_distance:
			global_position = _target_global_position
			_target_global_position = Vector2.ZERO
	elif not _move_dir.is_zero_approx():
		global_position += _move_dir * move_spped * delta
