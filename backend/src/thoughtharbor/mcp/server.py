"""Official Python MCP server entrypoint."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ThoughtHarbor")


def main() -> None:
    """Run the MCP server using the SDK's default transport."""

    mcp.run()


if __name__ == "__main__":
    main()
