"""Tests for skills/poc-sources/scripts/spike_sources.py. Run: python3 -m unittest discover -s tests"""
import importlib.util
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPT = os.path.join(ROOT, "skills", "poc-sources", "scripts", "spike_sources.py")
spec = importlib.util.spec_from_file_location("spike_sources", SCRIPT)
ss = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ss)

# Tool names in the shape real connectors expose, with made-up server ids.
READ_TOOLS = [
    "mcp__srvA__notion-fetch", "mcp__srvA__notion-search", "mcp__srvA__notion-query-data-sources",
    "mcp__srvA__notion-get-comments", "mcp__srvA__notion-list-recent-pages", "mcp__srvA__notion-get-self",
    "mcp__srvB__slack_read_channel", "mcp__srvB__slack_read_thread", "mcp__srvB__slack_search_public_and_private",
    "mcp__srvB__slack_search_users", "mcp__srvC__search_threads", "mcp__srvC__get_thread", "mcp__srvC__list_labels",
    "mcp__srvD__search_files", "mcp__srvD__read_file_content", "mcp__srvD__get_file_metadata", "mcp__srvD__list_recent_files",
    "mcp__srvE__get_meetings", "mcp__srvE__search_transcripts", "mcp__srvE__get_meeting_transcript",
    "mcp__srvF__resolve-library-id", "mcp__srvF__query-docs", "mcp__srvG__list_events", "mcp__srvG__search_events",
    "mcp__srvH__list-deals", "mcp__srvH__get-deal", "mcp__srvH__crm-sql-list-tables",
]
WRITE_TOOLS = [
    "mcp__srvA__notion-create-pages", "mcp__srvA__notion-update-page", "mcp__srvA__notion-delete-pages",
    "mcp__srvA__notion-move-pages", "mcp__srvA__notion-create-comment", "mcp__srvA__notion-spawn-session",
    "mcp__srvB__slack_send_message", "mcp__srvB__slack_send_message_draft", "mcp__srvB__slack_add_reaction",
    "mcp__srvB__slack_schedule_message", "mcp__srvB__slack_create_canvas", "mcp__srvC__send_message",
    "mcp__srvC__create_draft", "mcp__srvC__trash_thread", "mcp__srvC__apply_sensitive_message_label",
    "mcp__srvC__label_thread", "mcp__srvC__forward", "mcp__srvC__reply", "mcp__srvD__share_file", "mcp__srvD__trash_file",
    "mcp__srvD__update_file", "mcp__srvD__create_file", "mcp__srvD__request_access", "mcp__srvE__update_summary",
    "mcp__srvE__generate_summary", "mcp__srvE__sign_out", "mcp__srvG__create_event", "mcp__srvG__respond_to_event",
    "mcp__srvH__update-deal", "mcp__srvH__create-note", "mcp__srvH__delete-agent", "mcp__srvH__link-deal-channel",
    "mcp__srvH__capabilities_invoke_write", "mcp__srvI__assign_permission_set",
]
REVIEW_TOOLS = [
    "mcp__srvH__crm-sql-execute-query", "mcp__srvI__run_soql_query", "mcp__srvJ__code-mode",
    "mcp__srvJ__sequentialthinking", "mcp__srvK__capabilities_invoke_read", "mcp__srvB__slack_download_thing",
    "mcp__srvC__download_gmail_attachment", "mcp__srvA__notion-wait-session",
]


class BucketTest(unittest.TestCase):
    def test_read_tools_are_read(self):
        for n in READ_TOOLS:
            self.assertEqual(ss.bucket(ss.split_tool(n)[1]), "read", n)

    def test_write_tools_are_never_read_or_review(self):
        for n in WRITE_TOOLS:
            self.assertEqual(ss.bucket(ss.split_tool(n)[1]), "write", n)

    def test_dispatchers_and_unknowns_need_review(self):
        for n in REVIEW_TOOLS:
            self.assertEqual(ss.bucket(ss.split_tool(n)[1]), "review", n)

    def test_write_word_wins_over_read_word(self):
        self.assertEqual(ss.bucket("get_and_delete_thing"), "write")
        self.assertEqual(ss.bucket("search_then_send"), "write")

    def test_split_tool(self):
        self.assertEqual(ss.split_tool("mcp__abc-1__get_x"), ("abc-1", "get_x"))
        self.assertEqual(ss.split_tool("Read"), ("(unknown)", "Read"))

    def test_classify_groups_by_server(self):
        g = ss.classify(READ_TOOLS + WRITE_TOOLS[:3] + ["", "# comment"])
        self.assertIn("srvA", g)
        self.assertEqual(len(g["srvA"]["write"]), 3)
        self.assertNotIn("", g)


class AgentTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.base = os.path.join(self.d, "base.md")
        with open(self.base, "w") as f:
            f.write("---\nname: researcher\ndescription: base\nmodel: sonnet\ntools: Read, Bash\nskills:\n  - research-protocol\n---\nBody line.\n")
        self.approved = os.path.join(self.d, "approved.txt")
        self.out = os.path.join(self.d, "agents", "researcher-internal.md")
        self.src = os.path.join(self.d, "research-sources.md")

    def run_render(self, tools, **kw):
        with open(self.approved, "w") as f:
            f.write("\n".join(tools) + "\n")
        argv = ["render-agent", "--approved", self.approved, "--out", self.out, "--base", self.base, "--sources", self.src]
        if kw.get("force"):
            argv.append("--force")
        return ss.main(argv)

    def test_renders_tools_marker_and_sources_path(self):
        self.assertEqual(self.run_render(READ_TOOLS[:3]), 0)
        text = open(self.out).read()
        self.assertIn("name: researcher-internal", text)
        self.assertIn(ss.MARKER, text)
        self.assertIn(self.src, text)
        tools_line = [l for l in text.splitlines() if l.startswith("tools: ")][0]
        for t in READ_TOOLS[:3]:
            self.assertIn(t, tools_line)
        self.assertIn("Read, Bash, WebFetch, WebSearch, ToolSearch", tools_line)
        self.assertIn("Body line.", text)

    def test_refuses_write_tools(self):
        self.assertEqual(self.run_render([READ_TOOLS[0], WRITE_TOOLS[0]]), 2)
        self.assertFalse(os.path.exists(self.out))

    def test_refuses_non_mcp_names(self):
        self.assertEqual(self.run_render(["Write"]), 1)

    def test_refuses_to_overwrite_foreign_file(self):
        os.makedirs(os.path.dirname(self.out))
        with open(self.out, "w") as f:
            f.write("my own agent\n")
        self.assertEqual(self.run_render(READ_TOOLS[:1]), 2)
        self.assertEqual(open(self.out).read(), "my own agent\n")
        self.assertEqual(self.run_render(READ_TOOLS[:1], force=True), 0)

    def test_rerun_replaces_own_file(self):
        self.assertEqual(self.run_render(READ_TOOLS[:2]), 0)
        self.assertEqual(self.run_render(READ_TOOLS[:1]), 0)
        self.assertNotIn(READ_TOOLS[1], open(self.out).read())

    def test_review_tools_allowed_when_user_approves_them(self):
        self.assertEqual(self.run_render([REVIEW_TOOLS[1]]), 0)

    def test_init_sources_never_overwrites(self):
        self.assertEqual(ss.main(["init-sources", "--out", self.src]), 0)
        with open(self.src, "a") as f:
            f.write("my note\n")
        self.assertEqual(ss.main(["init-sources", "--out", self.src]), 0)
        self.assertIn("my note", open(self.src).read())

    def test_real_plugin_base_agent_has_expected_shape(self):
        base = os.path.join(ROOT, "agents", "researcher.md")
        self.assertEqual(ss.main(["render-agent", "--approved", self._approved(["mcp__x__get_a"]), "--out", self.out, "--base", base, "--sources", self.src]), 0)
        text = open(self.out).read()
        self.assertTrue(text.startswith("---\nname: researcher-internal\n"))
        self.assertIn("disallowedTools: Edit, Write, NotebookEdit", text)
        self.assertNotIn("no connector tools", text)
        self.assertIn("connector tools are read-only", text)

    def _approved(self, tools):
        with open(self.approved, "w") as f:
            f.write("\n".join(tools) + "\n")
        return self.approved

    def test_status_reports_gone_and_new(self):
        self.assertEqual(self.run_render(["mcp__srvA__notion-fetch", "mcp__srvA__notion-search"]), 0)
        vis = os.path.join(self.d, "vis.txt")
        with open(vis, "w") as f:
            f.write("mcp__srvA__notion-fetch\nmcp__srvA__notion-get-self\nmcp__srvA__notion-create-pages\n")
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ss.main(["status", "--agent", self.out, "--sources", self.src, "--file", vis])
        o = buf.getvalue()
        self.assertIn("no longer visible (1): notion-search", o)
        self.assertIn("new read-class tools (1): notion-get-self", o)


if __name__ == "__main__":
    unittest.main()
