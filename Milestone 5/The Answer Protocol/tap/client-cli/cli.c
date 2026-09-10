/* cli.c - TAP CLI client.
 *
 * Command Interface Choice (see README "Protocol Implementation"): this
 * client sends user input directly to the server using RFC protocol
 * syntax (option 1 from V.3). This keeps the client thin and transparent:
 * what you type is what goes over the wire, which is convenient for
 * debugging/testing the protocol directly (see also `make test`).
 *
 * It stays responsive to asynchronous EVT messages while waiting for user
 * input by running the socket read and the terminal read in parallel via
 * select() on both file descriptors.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <sys/socket.h>
#include <sys/select.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <strings.h>
#include <time.h>

#define BUF_SIZE 4096

static int connect_to(const char *host, int port) {
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) { perror("socket"); exit(1); }
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_port = htons((uint16_t)port);
    if (inet_pton(AF_INET, host, &addr.sin_addr) != 1) {
        fprintf(stderr, "error: invalid host '%s' (use an IPv4 address, e.g. 127.0.0.1)\n", host);
        exit(1);
    }
    if (connect(fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("connect");
        exit(1);
    }
    return fd;
}

int main(int argc, char **argv) {
    const char *host = "127.0.0.1";
    int port = 4242;
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--host") == 0 && i + 1 < argc) host = argv[++i];
        else if (strcmp(argv[i], "--port") == 0 && i + 1 < argc) port = atoi(argv[++i]);
        else if (strcmp(argv[i], "--help") == 0) {
            printf("usage: %s [--host H] [--port N]\n", argv[0]);
            return 0;
        }
    }

    int fd = connect_to(host, port);
    printf("Connected to TAP server at %s:%d\n", host, port);
    printf("Type commands (CONNECT <name>, LOOK, MOVE <dir>, CHAT <SCOPE> <msg>, TAKE/DROP <item>,\n");
    printf("INVENTORY, TALK/ATTACK/QUEST <npc>, DEFEND, FLEE, STATUS, QUESTS, WHO, GROUP ..., QUIT).\n\n");

    char netbuf[BUF_SIZE];
    size_t netlen = 0;

    while (1) {
        fd_set readfds;
        FD_ZERO(&readfds);
        FD_SET(fd, &readfds);
        FD_SET(STDIN_FILENO, &readfds);
        int maxfd = fd > STDIN_FILENO ? fd : STDIN_FILENO;

        int ready = select(maxfd + 1, &readfds, NULL, NULL, NULL);
        if (ready < 0) {
            if (errno == EINTR) continue;
            perror("select");
            break;
        }

        if (FD_ISSET(fd, &readfds)) {
            char chunk[BUF_SIZE];
            ssize_t n = recv(fd, chunk, sizeof(chunk) - 1, 0);
            if (n <= 0) {
                printf("\n[disconnected from server]\n");
                break;
            }
            chunk[n] = '\0';
            if (netlen + (size_t)n < sizeof(netbuf)) {
                memcpy(netbuf + netlen, chunk, (size_t)n + 1);
                netlen += (size_t)n;
            } else {
                netlen = 0; /* defensive reset on overflow */
            }
            char *start = netbuf;
            char *nl;
            while ((nl = strchr(start, '\n')) != NULL) {
                *nl = '\0';
                printf("%s\n", start);
                start = nl + 1;
            }
            size_t remaining = strlen(start);
            memmove(netbuf, start, remaining + 1);
            netlen = remaining;
            fflush(stdout);
        }

        if (FD_ISSET(STDIN_FILENO, &readfds)) {
            char line[1024];
            if (!fgets(line, sizeof(line), stdin)) {
                printf("\n[input closed, sending QUIT]\n");
                send(fd, "QUIT\n", 5, 0);
                break;
            }
            size_t len = strlen(line);
            if (len == 0 || line[len - 1] != '\n') {
                if (len < sizeof(line) - 1) { line[len] = '\n'; line[len + 1] = '\0'; }
            }
            if (send(fd, line, strlen(line), 0) < 0) {
                perror("send");
                break;
            }
            if (strncasecmp(line, "QUIT", 4) == 0) {
                /* give the server a moment to reply "OK bye" before we exit */
                struct timespec ts = { .tv_sec = 0, .tv_nsec = 200000000L };
                nanosleep(&ts, NULL);
                char chunk[BUF_SIZE];
                ssize_t n = recv(fd, chunk, sizeof(chunk) - 1, MSG_DONTWAIT);
                if (n > 0) { chunk[n] = '\0'; printf("%s", chunk); }
                break;
            }
        }
    }

    close(fd);
    return 0;
}
