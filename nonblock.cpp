#include <iostream>
#include <unistd.h>
#include <arpa/inet.h>
#include <fcntl.h>
#include <sys/epoll.h>
#include <vector>
#include <string.h>
#include <string>

int set_nonblocking(int fd) {
    int flags = fcntl(fd, F_GETFL, 0);
    return fcntl(fd, F_SETFL, flags | O_NONBLOCK);
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
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    sockaddr_in address{};
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(port);

    if (bind(server_fd, (struct sockaddr*)&address, sizeof(address)) < 0) {
        perror("Bind failed");
        return 1;
    }

    if (listen(server_fd, 100) < 0) {
        perror("Listen failed");
        return 1;
    }

    set_nonblocking(server_fd);

    int epoll_fd = epoll_create1(0);
    if (epoll_fd < 0) {
        perror("epoll_create1 failed");
        return 1;
    }

    epoll_event ev{}, events[64];
    ev.events = EPOLLIN;
    ev.data.fd = server_fd;
    if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, server_fd, &ev) < 0) {
        perror("epoll_ctl add server_fd failed");
        return 1;
    }

    std::cout << "Non-blocking I/O Server listening on port " << port
              << " with buffer size " << buffer_size << " bytes\n";

    while (true) {
        int n = epoll_wait(epoll_fd, events, 64, -1);
        if (n < 0) {
            perror("epoll_wait failed");
            continue;
        }

        for (int i = 0; i < n; i++) {
            int client_fd = events[i].data.fd;

            if (client_fd == server_fd) {
                // Accept new client
                while (true) {
                    int new_fd = accept(server_fd, nullptr, nullptr);
                    if (new_fd < 0) {
                        break; // No more clients to accept
                    }
                    set_nonblocking(new_fd);
                    epoll_event client_ev{};
                    client_ev.events = EPOLLIN;
                    client_ev.data.fd = new_fd;
                    if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, new_fd, &client_ev) < 0) {
                        perror("epoll_ctl add client failed");
                        close(new_fd);
                    }
                }
            } else {
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
                        perror("send failed");
                    }
                }

                // Remove from epoll and close connection
                epoll_ctl(epoll_fd, EPOLL_CTL_DEL, client_fd, nullptr);
                close(client_fd);
            }
        }
    }

    close(server_fd);
    return 0;
}

