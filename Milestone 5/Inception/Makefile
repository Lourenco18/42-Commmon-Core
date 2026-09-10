# ============================================================================
#  Inception - Makefile
#  Builds and manages the whole Docker infrastructure from the project root.
# ============================================================================

# --- Replace with your own 42 login (also change it in srcs/.env) --------
LOGIN          := yourlogin

DATA_DIR       := /home/$(LOGIN)/data
COMPOSE_FILE   := srcs/docker-compose.yml
ENV_FILE       := srcs/.env
COMPOSE        := docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE)

.PHONY: all up build down stop start restart logs ps clean fclean prepare re

all: up

# Create the host directories that will back the named volumes
# (must exist before Compose starts, since we bind them via driver_opts).
prepare:
	@mkdir -p $(DATA_DIR)/db
	@mkdir -p $(DATA_DIR)/wordpress
	@echo "Data directories ready in $(DATA_DIR)"

up: prepare
	$(COMPOSE) up -d --build

build: prepare
	$(COMPOSE) build

down:
	$(COMPOSE) down

stop:
	$(COMPOSE) stop

start:
	$(COMPOSE) start

restart: down up

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

# Remove containers, networks and dangling images/build cache
clean: down
	docker system prune -f

# Full reset: also wipes the persisted data on the host
fclean: clean
	docker volume prune -f
	sudo rm -rf $(DATA_DIR)/db $(DATA_DIR)/wordpress

re: fclean all
