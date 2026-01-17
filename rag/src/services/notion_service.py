"""
Notion Integration Service

Handles all Notion API interactions including:
- OAuth flow
- Page/database listing
- Content extraction and conversion to Markdown
- Webhook processing with debounce
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from notion_client import Client
from notion_client.errors import APIResponseError

logger = logging.getLogger(__name__)


class NotionService:
    """Service for interacting with Notion API."""
    
    SCOPES = ["read_content", "read_user"]
    
    def __init__(self, access_token: Optional[str] = None):
        self.client = Client(auth=access_token) if access_token else None
    
    def set_token(self, access_token: str):
        """Update the access token and reinitialize client."""
        self.client = Client(auth=access_token)
    
    # =========================================================================
    # PAGE & DATABASE LISTING
    # =========================================================================
    
    async def list_accessible_pages(self) -> List[Dict[str, Any]]:
        """
        List all pages the integration has access to.
        Returns simplified page objects with id, title, icon, last_edited.
        """
        if not self.client:
            raise ValueError("Notion client not initialized. Set access token first.")
        
        try:
            results = []
            has_more = True
            start_cursor = None
            
            while has_more:
                response = self.client.search(
                    filter={"property": "object", "value": "page"},
                    start_cursor=start_cursor,
                    page_size=100
                )
                
                for page in response.get("results", []):
                    results.append(self._simplify_page(page))
                
                has_more = response.get("has_more", False)
                start_cursor = response.get("next_cursor")
            
            return results
            
        except APIResponseError as e:
            logger.error(f"Notion API error listing pages: {e}")
            raise
    
    async def list_accessible_databases(self) -> List[Dict[str, Any]]:
        """
        List all databases the integration has access to.
        Returns simplified database objects.
        """
        if not self.client:
            raise ValueError("Notion client not initialized. Set access token first.")
        
        try:
            results = []
            has_more = True
            start_cursor = None
            
            while has_more:
                response = self.client.search(
                    filter={"property": "object", "value": "data_source"},
                    start_cursor=start_cursor,
                    page_size=100
                )
                
                for db in response.get("results", []):
                    results.append(self._simplify_database(db))
                
                has_more = response.get("has_more", False)
                start_cursor = response.get("next_cursor")
            
            return results
            
        except APIResponseError as e:
            logger.error(f"Notion API error listing databases: {e}")
            raise
    
    # =========================================================================
    # CONTENT EXTRACTION
    # =========================================================================
    
    async def get_page_content(self, page_id: str) -> Dict[str, Any]:
        """
        Fetch page metadata and all blocks.
        Returns page info and full content as Markdown.
        """
        if not self.client:
            raise ValueError("Notion client not initialized.")
        
        try:
            # Get page metadata
            page = self.client.pages.retrieve(page_id)
            
            # Get all blocks
            blocks = await self._get_all_blocks(page_id)
            
            # Convert blocks to Markdown
            markdown_content = self._blocks_to_markdown(blocks)
            
            return {
                "id": page_id,
                "title": self._extract_title(page),
                "last_edited": page.get("last_edited_time"),
                "created_time": page.get("created_time"),
                "content_markdown": markdown_content,
                "block_count": len(blocks)
            }
            
        except APIResponseError as e:
            logger.error(f"Notion API error fetching page {page_id}: {e}")
            raise
    
    async def _get_all_blocks(self, block_id: str, depth: int = 0) -> List[Dict]:
        """Recursively fetch all blocks including nested children."""
        if depth > 3:  # Limit nesting depth
            return []
        
        blocks = []
        has_more = True
        start_cursor = None
        
        while has_more:
            response = self.client.blocks.children.list(
                block_id=block_id,
                start_cursor=start_cursor,
                page_size=100
            )
            
            for block in response.get("results", []):
                blocks.append(block)
                
                # Recursively get children if block has them
                if block.get("has_children", False):
                    children = await self._get_all_blocks(block["id"], depth + 1)
                    block["children"] = children
            
            has_more = response.get("has_more", False)
            start_cursor = response.get("next_cursor")
        
        return blocks
    
    # =========================================================================
    # MARKDOWN CONVERSION
    # =========================================================================
    
    def _blocks_to_markdown(self, blocks: List[Dict], indent: int = 0) -> str:
        """Convert Notion blocks to Markdown string."""
        lines = []
        indent_str = "  " * indent
        
        for block in blocks:
            block_type = block.get("type", "")
            
            if block_type == "paragraph":
                text = self._rich_text_to_md(block.get("paragraph", {}).get("rich_text", []))
                lines.append(f"{indent_str}{text}")
                
            elif block_type == "heading_1":
                text = self._rich_text_to_md(block.get("heading_1", {}).get("rich_text", []))
                lines.append(f"\n# {text}")
                
            elif block_type == "heading_2":
                text = self._rich_text_to_md(block.get("heading_2", {}).get("rich_text", []))
                lines.append(f"\n## {text}")
                
            elif block_type == "heading_3":
                text = self._rich_text_to_md(block.get("heading_3", {}).get("rich_text", []))
                lines.append(f"\n### {text}")
                
            elif block_type == "bulleted_list_item":
                text = self._rich_text_to_md(block.get("bulleted_list_item", {}).get("rich_text", []))
                lines.append(f"{indent_str}- {text}")
                
            elif block_type == "numbered_list_item":
                text = self._rich_text_to_md(block.get("numbered_list_item", {}).get("rich_text", []))
                lines.append(f"{indent_str}1. {text}")
                
            elif block_type == "to_do":
                text = self._rich_text_to_md(block.get("to_do", {}).get("rich_text", []))
                checked = "x" if block.get("to_do", {}).get("checked", False) else " "
                lines.append(f"{indent_str}- [{checked}] {text}")
                
            elif block_type == "toggle":
                text = self._rich_text_to_md(block.get("toggle", {}).get("rich_text", []))
                lines.append(f"{indent_str}**{text}**")
                
            elif block_type == "code":
                code_block = block.get("code", {})
                language = code_block.get("language", "")
                text = self._rich_text_to_md(code_block.get("rich_text", []))
                lines.append(f"\n```{language}\n{text}\n```")
                
            elif block_type == "quote":
                text = self._rich_text_to_md(block.get("quote", {}).get("rich_text", []))
                lines.append(f"{indent_str}> {text}")
                
            elif block_type == "callout":
                text = self._rich_text_to_md(block.get("callout", {}).get("rich_text", []))
                lines.append(f"\n> **Note:** {text}")
                
            elif block_type == "divider":
                lines.append("\n---\n")
                
            elif block_type == "table":
                table_content = self._table_to_markdown(block)
                lines.append(table_content)
                
            elif block_type == "image":
                image_data = block.get("image", {})
                url = image_data.get("file", {}).get("url") or image_data.get("external", {}).get("url", "")
                caption = self._rich_text_to_md(image_data.get("caption", []))
                lines.append(f"\n![{caption}]({url})")
            
            # Process children recursively
            if block.get("children"):
                child_md = self._blocks_to_markdown(block["children"], indent + 1)
                lines.append(child_md)
        
        return "\n".join(lines)
    
    def _rich_text_to_md(self, rich_text: List[Dict]) -> str:
        """Convert Notion rich text array to Markdown string."""
        result = []
        
        for text_obj in rich_text:
            content = text_obj.get("text", {}).get("content", "")
            annotations = text_obj.get("annotations", {})
            
            # Apply formatting
            if annotations.get("bold"):
                content = f"**{content}**"
            if annotations.get("italic"):
                content = f"*{content}*"
            if annotations.get("strikethrough"):
                content = f"~~{content}~~"
            if annotations.get("code"):
                content = f"`{content}`"
            
            # Handle links
            link = text_obj.get("text", {}).get("link")
            if link:
                content = f"[{content}]({link.get('url', '')})"
            
            result.append(content)
        
        return "".join(result)
    
    def _table_to_markdown(self, block: Dict) -> str:
        """Convert Notion table block to Markdown table."""
        # Note: Table rows need to be fetched as children
        table_width = block.get("table", {}).get("table_width", 0)
        children = block.get("children", [])
        
        if not children:
            return ""
        
        lines = []
        for i, row in enumerate(children):
            if row.get("type") == "table_row":
                cells = row.get("table_row", {}).get("cells", [])
                row_text = " | ".join(self._rich_text_to_md(cell) for cell in cells)
                lines.append(f"| {row_text} |")
                
                # Add header separator after first row
                if i == 0:
                    separator = " | ".join(["---"] * len(cells))
                    lines.append(f"| {separator} |")
        
        return "\n".join(lines)
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _simplify_page(self, page: Dict) -> Dict[str, Any]:
        """Extract relevant page info into a simple dict."""
        return {
            "id": page.get("id", ""),
            "title": self._extract_title(page),
            "icon": self._extract_icon(page),
            "last_edited": page.get("last_edited_time"),
            "created_time": page.get("created_time"),
            "object_type": "page"
        }
    
    def _simplify_database(self, db: Dict) -> Dict[str, Any]:
        """Extract relevant database info into a simple dict."""
        title = ""
        title_arr = db.get("title", [])
        if title_arr:
            title = title_arr[0].get("plain_text", "Untitled Database")
        
        return {
            "id": db.get("id", ""),
            "title": title or "Untitled Database",
            "icon": self._extract_icon(db),
            "last_edited": db.get("last_edited_time"),
            "object_type": "database"
        }
    
    def _extract_title(self, page: Dict) -> str:
        """Extract title from page properties."""
        properties = page.get("properties", {})
        
        # Try common title property names
        for prop_name in ["title", "Name", "name", "Title"]:
            if prop_name in properties:
                prop = properties[prop_name]
                if prop.get("type") == "title":
                    title_arr = prop.get("title", [])
                    if title_arr:
                        return title_arr[0].get("plain_text", "Untitled")
        
        return "Untitled"
    
    def _extract_icon(self, obj: Dict) -> Optional[str]:
        """Extract icon emoji or URL from page/database."""
        icon = obj.get("icon")
        if not icon:
            return None
        
        if icon.get("type") == "emoji":
            return icon.get("emoji")
        elif icon.get("type") == "external":
            return icon.get("external", {}).get("url")
        elif icon.get("type") == "file":
            return icon.get("file", {}).get("url")
        
        return None


# =============================================================================
# WEBHOOK DEBOUNCE MANAGER
# =============================================================================

class NotionWebhookDebouncer:
    """
    Manages debouncing of Notion webhook events.
    Waits 2 minutes after last change notification before triggering re-sync.
    """
    
    DEBOUNCE_SECONDS = 120  # 2 minutes
    
    def __init__(self):
        # page_id -> (last_webhook_time, scheduled_task)
        self._pending_syncs: Dict[str, datetime] = {}
    
    def record_change(self, page_id: str) -> None:
        """Record a change notification for a page. Resets the debounce timer."""
        self._pending_syncs[page_id] = datetime.utcnow()
        logger.info(f"Notion webhook: page {page_id} changed, debounce timer reset")
    
    def get_pages_ready_for_sync(self) -> List[str]:
        """
        Get list of page IDs that haven't had changes for 2+ minutes.
        These are ready to be re-synced.
        """
        ready = []
        now = datetime.utcnow()
        threshold = now - timedelta(seconds=self.DEBOUNCE_SECONDS)
        
        for page_id, last_change in list(self._pending_syncs.items()):
            if last_change < threshold:
                ready.append(page_id)
                del self._pending_syncs[page_id]
        
        return ready
    
    def clear_page(self, page_id: str) -> None:
        """Remove a page from pending syncs (after sync completes)."""
        self._pending_syncs.pop(page_id, None)


# Global debouncer instance
webhook_debouncer = NotionWebhookDebouncer()
