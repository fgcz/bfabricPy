- The app generates a sequence of `InputSpec`
- These get transformed into `InputListing` resolving into file operation and static file contents
- This way we can ensure proper separation of concerns and timestamp preservation, which is useful for workflows

Limitations:

- The current logic will simply put all "StaticFile" content into RAM, which is generally fine for now, but might
    need to be extended with a TempFile mechanism to specify a local file instead (i guess we would create a separate class).
- Laziness would complicate the logic, and would only help for the list operation. Check will anyways need the Listing
    and file preparation will need it too. If necessary, one could filter the specs before processing them further and for
    this file name resolution would be necessary, which is a bit limiting. So for now I would say we don't support any
    form of laziness.
-
