"""Long-press menus of the chat and node lists: what the MeshCore apps offer on a contact or a
channel (open, mark read, sounds, route, ping, map, history, remove)."""

from mpos import Intent

import map_model
import ui_model
import ui_theme as T

_SOUNDS = (("Follow the settings", "default"), ("Always beep", "on"), ("Never beep", "off"))


def _open(activity, cls, **extras):
    intent = Intent(activity_class=cls)
    for k, v in extras.items():
        intent.putExtra(k, v)
    activity.startActivity(intent)


def sounds_menu(mgr, key, title):
    cur = mgr.sound_override(key)
    return T.ActionSheet(title, [(text, lambda v=value: mgr.set_sound_override(key, v),
                                  "checked" if value == cur else None)
                                 for text, value in _SOUNDS], "Sounds")


def chat_menu(activity, mgr, key, kind, open_chat):
    """A chat in the Chats list: a channel (key = its name) or a contact (key = pubkey)."""
    import routing_pages
    import thread_activity
    if kind == "channel":
        title = key
    else:
        title = ui_model.display((mgr.get_contact(key) or {}).get("name")) or key[:8]
    actions = [("Open", lambda: open_chat(key, kind))]
    if mgr.get_unread(key):
        actions.append(("Mark as read", lambda: mgr.clear_unread(key)))
    actions.append(("Sounds…", lambda: sounds_menu(mgr, key, title)))
    if kind == "channel":
        actions.append(("Region scope…",
                        lambda: _open(activity, routing_pages.ChannelScopeActivity, channel=key)))
        actions.append(("Channel info",
                        lambda: _open(activity, thread_activity.ChannelInfoActivity, channel=key)))
        actions.append(("Clear history", lambda: mgr.clear_history(key), "danger"))
        if key != "Public":
            actions.append(("Leave channel", lambda: mgr.remove_channel(key), "danger"))
    else:
        actions += node_actions(activity, mgr, key, chat=False)
        actions.append(("Clear history", lambda: mgr.clear_history(key), "danger"))
        actions.append(("Remove contact", lambda: mgr.remove_contact(key), "danger"))
    return T.ActionSheet(title, actions, "Channel" if kind == "channel" else "Contact")


def node_actions(activity, mgr, pk, chat=True):
    """Actions on a node or contact: chat or details, route, ping, map."""
    import map_view
    import node_activity
    import routing_pages
    import thread_activity
    node = mgr.get_node(pk) or mgr.get_contact(pk) or {}
    kind = {1: "chat", 2: "rptr", 3: "room", 4: "sensor"}.get(node.get("type"), "chat")
    out = []
    if chat and kind == "chat":
        out.append(("Open chat", lambda: map_view.open_node(activity, mgr, pk, "chat")))
    if kind != "chat":
        out.append(("Details", lambda: _open(activity, node_activity.NodeDetailActivity,
                                              pubkey=pk)))
    if mgr.is_contact(pk) and kind in ("chat", "room"):
        out.append(("Route…", lambda: _open(activity, routing_pages.RoutingActivity,
                                                pubkey=pk)))
    out.append(("Ping", lambda: mgr.ping(pk)))
    if map_model.positions([node]):
        out.append(("Show on map", lambda: _open(activity, map_view.MapActivity, pubkey=pk)))
    return out


def node_menu(activity, mgr, pk, discovered=False):
    """A node in the contacts or the discovered list."""
    node = mgr.get_node(pk) or mgr.get_contact(pk) or {}
    title = ui_model.display(node.get("name")) or pk[:8]
    actions = node_actions(activity, mgr, pk)
    if mgr.is_contact(pk):
        actions.append(("Sounds…", lambda: sounds_menu(mgr, pk, title)))
        actions.append(("Remove contact", lambda: mgr.remove_contact(pk), "danger"))
    else:
        actions.append(("Add to contacts", lambda: mgr.add_contact(pk, node.get("name"),
                                                                    node.get("type", 1))))
    if discovered:
        actions.append(("Remove from discovered", lambda: mgr.forget_node(pk), "danger"))
    return T.ActionSheet(title, actions, "%s · %s" % (
        {1: "companion", 2: "repeater", 3: "room server", 4: "sensor"}.get(node.get("type"),
                                                                          "node"), pk[:8].upper()))
