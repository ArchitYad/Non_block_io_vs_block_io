#include <iostream>
#include <unistd.h>
#include <arpa/inet.h>
#include <string.h>
#include <vector>
#include <thread>
#include <mutex>

void handle_client(int client_fd, int buffer_size) {
    std::vector<char> buffer(buffer_size);

    int valread = read(client_fd, buffer.data(), buffer_size);
    if (valread > 0) {
        std::string response =
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/plain\r\n"
            "Content-Length: 12\r\n"
            "Connection: close\r\n"
            "\r\n"
            "Hello World!";

        ssize_t sent = send(client_fd, response.c_str(), response.size(), 0);
        if (sent < 0) {
            perror("Send failed");
        }
    }

    close(client_fd);
}

int main(int argc, char* argv[]) {
    int port = 8080;
    int buffer_size = 1024;

    if (argc >= 2) port = std::stoi(argv[1]);
    if (argc >= 3) buffer_size = std::stoi(argv[2]);

    int server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd == -1) {
        perror("Socket failed");
        return 1;
    }

    int opt = 1;
    if (setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) < 0) {
        perror("setsockopt failed");
        close(server_fd);
        return 1;
    }

    sockaddr_in address{};
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(port);

    if (bind(server_fd, (struct sockaddr*)&address, sizeof(address)) < 0) {
        perror("Bind failed");
        close(server_fd);
        return 1;
    }

    if (listen(server_fd, 100) < 0) {
        perror("Listen failed");
        close(server_fd);
        return 1;
    }

    std::cout << "Blocking Threaded Server listening on port " << port
              << " with buffer size " << buffer_size << " bytes\n";

    while (true) {
        int client_fd = accept(server_fd, nullptr, nullptr);
        if (client_fd < 0) {
            perror("Accept failed");
            continue;
        }

        // Launch new thread per connection
        std::thread client_thread(handle_client, client_fd, buffer_size);
        client_thread.detach(); // Allow thread to run independently
    }

    close(server_fd);
    return 0;
}

