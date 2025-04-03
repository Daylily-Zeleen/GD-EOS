# This node alaways owned by lobby owner.
# The authority will be updated in these cases:
#		peer connected
#		peer disconnected
#		lobby memnber is promoted
extends MultiplayerSpawner

var _local_user_id: EOSProductUserId
var _local_peer: EOSMultiplayerPeer

# peer_id -> Player Node
var _players: Dictionary = {}
var _lobby_id: String


func setup_local(product_user_id: EOSProductUserId, lobby_id: String) -> void:
	_local_user_id = product_user_id
	_lobby_id = lobby_id

	_local_peer = EOSMultiplayerPeer.new()
	_local_peer.create_mesh(lobby_id)
	multiplayer.multiplayer_peer = _local_peer
#
	_spawn_player(_local_peer.get_unique_id())

	_local_peer.peer_connected.connect(_spawn_player)
	_local_peer.peer_disconnected.connect(_despawn_player)
	EOSLobby.lobby_member_status_received.connect(_on_lobby_member_status_received)


func _spawn_player(peer_id: int) -> void:
	# Copy lobby details to get lobby owner.
	# We don't care the failed result here, just get lobby detail if operation success.
	var details := EOSLobby.copy_lobby_details(_lobby_id, _local_user_id)
	if not is_instance_valid(details):
		printerr("Copy lobby details failed: ", EOS.result_to_string(EOS.get_last_result_code()))
		return

	# Updata authority
	_update_authority(details.get_lobby_owner())

	if not details.get_lobby_owner().is_equal(_local_user_id):
		# Only lobby owner can spawn player.
		return

	var player := preload("player.tscn").instantiate() as Node
	_players[peer_id] = player
	player.name = str(peer_id)
	add_child(player, true)


func _despawn_player(peer_id: int) -> void:
	# Copy lobby details to get lobby owner.
	# We don't care the failed result here, just get lobby detail if operation success.
	var details := EOSLobby.copy_lobby_details(_lobby_id, _local_user_id)
	if not is_instance_valid(details):
		printerr("Copy lobby details failed: ", EOS.result_to_string(EOS.get_last_result_code()))
		return

	# Updata authority
	_update_authority(details.get_lobby_owner())

	if not details.get_lobby_owner().is_equal(_local_user_id):
		# Only lobby owner can despawn player.
		return

	assert(_players.has(peer_id))
	var player := _players.get(peer_id) as Node
	if player and not player.is_queued_for_deletion():
		remove_child(player)
		player.queue_free()
	_players.erase(peer_id)


func _on_lobby_member_status_received(data: EOSLobby_LobbyMemberStatusReceivedCallbackInfo) -> void:
	if data.lobby_id != _lobby_id:
		return

	match data.current_status:
		EOSLobby.LMS_PROMOTED:
			# Updata authority.
			_update_authority(data.target_user_id)
		EOSLobby.LMS_JOINED:
			# Add a mesh peer.
			_local_peer.add_mesh_peer(data.target_user_id)
		EOSLobby.LMS_LEFT, EOSLobby.LMS_DISCONNECTED, EOSLobby.LMS_KICKED:
			# Disconnect a peer if it is connected.
			var peer_id := _local_peer.get_peer_id(data.target_user_id)
			if _local_peer.has_peer(peer_id):
				_local_peer.disconnect_peer(peer_id)
		EOSLobby.LMS_CLOSED:
			# Disconnect all peer due to lobby closed.
			for peer_id in _players:
				if _local_peer.has_peer(peer_id):
					_local_peer.disconnect_peer(peer_id)


# ====================
func _update_authority(user_id: EOSProductUserId) -> void:
	var host_peer_id := 0
	if EOSMultiplayerPeer.get_local_user_id().is_equal(user_id):
		host_peer_id = _local_peer.get_unique_id()
	else:
		host_peer_id = _local_peer.get_peer_id(user_id)

	set_multiplayer_authority(host_peer_id, false)
