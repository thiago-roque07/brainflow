#include <simplebluez/Bluez.h>
#include <simplebluez/ProxyOrg.h>
#include <simpledbus/interfaces/ObjectManager.h>

using namespace SimpleBluez;

Bluez::Bluez() : Proxy(std::make_shared<SimpleDBus::Connection>(DBUS_BUS_SYSTEM), "org.bluez", "/") {
    _interfaces["org.freedesktop.DBus.ObjectManager"] = std::static_pointer_cast<SimpleDBus::Interface>(
        std::make_shared<SimpleDBus::ObjectManager>(_conn, "org.bluez", "/"));

    object_manager()->InterfacesAdded = [&](std::string path, SimpleDBus::Holder options) { path_add(path, options); };
    object_manager()->InterfacesRemoved = [&](std::string path, SimpleDBus::Holder options) {
        path_remove(path, options);
    };
}

Bluez::~Bluez() { _conn->remove_match("type='signal',sender='org.bluez'"); }

void Bluez::init() {
    _conn->init();

    // Load all managed objects
    SimpleDBus::Holder managed_objects = object_manager()->GetManagedObjects();
    for (auto& [path, managed_interfaces] : managed_objects.get_dict_object_path()) {
        path_add(path, managed_interfaces);
    }

    _conn->add_match("type='signal',sender='org.bluez'");
}

void Bluez::run_async() {
    _conn->read_write();
    SimpleDBus::Message message = _conn->pop_message();
    while (message.is_valid()) {
        message_forward(message);
        message = _conn->pop_message();
    }
}

std::vector<std::shared_ptr<Adapter>> Bluez::get_adapters() {
    return std::dynamic_pointer_cast<ProxyOrg>(path_get("/org"))->get_adapters();
}

std::shared_ptr<SimpleDBus::Proxy> Bluez::path_create(const std::string& path) {
    auto child = std::make_shared<ProxyOrg>(_conn, _bus_name, path);
    return std::static_pointer_cast<SimpleDBus::Proxy>(child);
}

std::shared_ptr<SimpleDBus::ObjectManager> Bluez::object_manager() {
    return std::dynamic_pointer_cast<SimpleDBus::ObjectManager>(interface_get("org.freedesktop.DBus.ObjectManager"));
}
