if __name__ == "__main__":
    print("=== CYBER ARCHIVES - VAULT SECURITY SYSTEM ===\n")

    print("Initiating secure vault access...")
    print("Vault connection established with failsafe protocols\n")

    print("SECURE EXTRACTION:")
    try:
        with open("classified_data.txt", "r") as vault:
            content = vault.read()
        print(content.strip())

        print()
        print("SECURE PRESERVATION:")
    except FileNotFoundError:
        print("ERROR: Storage vault not found. ")

    with open("classified_data.txt", "a") as vault:
        vault.write("[CLASSIFIED] New security protocols archived\n")

    print("[CLASSIFIED] New security protocols archived")
    print("Vault automatically sealed upon completion\n")

    print("All vault operations completed with maximum security.")
