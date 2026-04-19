if __name__ == "__main__":
    print("=== CYBER ARCHIVES - CRISIS RESPONSE SYSTEM ===\n")

    def crisis_handler(filename: str) -> None:
        try:
            print(f"CRISIS ALERT: Attempting access to '{filename}'")

            with open(filename, "r") as file:
                content = file.read().strip()
                print(f"SUCCESS: Archive recovered - \"{content}\"")
                print("STATUS: Normal operations resumed\n")

        except FileNotFoundError:
            print("RESPONSE: Archive not found in storage matrix")
            print("STATUS: Crisis handled, system stable\n")

        except PermissionError:
            print("RESPONSE: Security protocols deny access")
            print("STATUS: Crisis handled, security maintained\n")

        except Exception:
            print("RESPONSE: Unexpected system anomaly detected")
            print("STATUS: Crisis contained, investigation ongoing\n")

    crisis_handler("lost_archive.txt")
    crisis_handler("classified_vault.txt")
    crisis_handler("standard_archive.txt")

    print("All crisis scenarios handled successfully. Archives secure.")
