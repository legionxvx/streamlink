import os.path
import tempfile
import unittest
from unittest.mock import Mock, call, patch

import streamlink_cli.main
from streamlink.plugin.plugin import Plugin
from streamlink_cli.main import (
    check_file_output, create_output, format_valid_streams, handle_stream, handle_url, resolve_stream_name
)
from streamlink_cli.output import FileOutput, PlayerOutput


class FakePlugin:
    @classmethod
    def stream_weight(cls, stream):
        return Plugin.stream_weight(stream)


class TestCLIMain(unittest.TestCase):
    def test_check_file_output(self):
        streamlink_cli.main.console = Mock()
        self.assertIsInstance(check_file_output("test", False), FileOutput)

    def test_check_file_output_exists(self):
        tmpfile = tempfile.NamedTemporaryFile()
        try:
            streamlink_cli.main.console = console = Mock()
            streamlink_cli.main.sys.stdin = stdin = Mock()
            stdin.isatty.return_value = True
            console.ask.return_value = "y"
            self.assertTrue(os.path.exists(tmpfile.name))
            self.assertIsInstance(check_file_output(tmpfile.name, False), FileOutput)
        finally:
            tmpfile.close()

    def test_check_file_output_exists_notty(self):
        tmpfile = tempfile.NamedTemporaryFile()
        try:
            streamlink_cli.main.console = Mock()
            streamlink_cli.main.sys.stdin = stdin = Mock()
            stdin.isatty.return_value = False
            self.assertTrue(os.path.exists(tmpfile.name))
            self.assertRaises(SystemExit, check_file_output, tmpfile.name, False)
        finally:
            tmpfile.close()

    def test_check_file_output_exists_force(self):
        tmpfile = tempfile.NamedTemporaryFile()
        try:
            streamlink_cli.main.console = Mock()
            self.assertTrue(os.path.exists(tmpfile.name))
            self.assertIsInstance(check_file_output(tmpfile.name, True), FileOutput)
        finally:
            tmpfile.close()

    @patch('sys.exit')
    def test_check_file_output_exists_no(self, sys_exit):
        tmpfile = tempfile.NamedTemporaryFile()
        try:
            streamlink_cli.main.console = console = Mock()
            console.ask.return_value = "n"
            self.assertTrue(os.path.exists(tmpfile.name))
            check_file_output(tmpfile.name, False)
            sys_exit.assert_called_with()
        finally:
            tmpfile.close()

    def test_resolve_stream_name(self):
        a = Mock()
        b = Mock()
        c = Mock()
        d = Mock()
        e = Mock()
        streams = {
            "160p": a,
            "360p": b,
            "480p": c,
            "720p": d,
            "1080p": e,
            "worst": b,
            "best": d,
            "worst-unfiltered": a,
            "best-unfiltered": e
        }

        self.assertEqual(resolve_stream_name(streams, "unknown"), "unknown")
        self.assertEqual(resolve_stream_name(streams, "160p"), "160p")
        self.assertEqual(resolve_stream_name(streams, "360p"), "360p")
        self.assertEqual(resolve_stream_name(streams, "480p"), "480p")
        self.assertEqual(resolve_stream_name(streams, "720p"), "720p")
        self.assertEqual(resolve_stream_name(streams, "1080p"), "1080p")
        self.assertEqual(resolve_stream_name(streams, "worst"), "360p")
        self.assertEqual(resolve_stream_name(streams, "best"), "720p")
        self.assertEqual(resolve_stream_name(streams, "worst-unfiltered"), "160p")
        self.assertEqual(resolve_stream_name(streams, "best-unfiltered"), "1080p")

    def test_format_valid_streams(self):
        a = Mock()
        b = Mock()
        c = Mock()

        streams = {
            "audio": a,
            "720p": b,
            "1080p": c,
            "worst": b,
            "best": c
        }
        self.assertEqual(
            format_valid_streams(FakePlugin, streams),
            ", ".join([
                "audio",
                "720p (worst)",
                "1080p (best)"
            ])
        )

        streams = {
            "audio": a,
            "720p": b,
            "1080p": c,
            "worst-unfiltered": b,
            "best-unfiltered": c
        }
        self.assertEqual(
            format_valid_streams(FakePlugin, streams),
            ", ".join([
                "audio",
                "720p (worst-unfiltered)",
                "1080p (best-unfiltered)"
            ])
        )

    @patch("streamlink_cli.main.args", stream_url=True, subprocess_cmdline=False)
    @patch("streamlink_cli.main.console", json=True)
    def test_handle_stream_with_json_and_stream_url(self, console, args):
        stream = Mock()
        streams = dict(best=stream)
        plugin = Mock(FakePlugin(), module="fake", arguments=[], streams=Mock(return_value=streams))

        handle_stream(plugin, streams, "best")
        self.assertEqual(console.msg.mock_calls, [])
        self.assertEqual(console.msg_json.mock_calls, [call(stream)])
        self.assertEqual(console.error.mock_calls, [])
        console.msg_json.mock_calls.clear()

        console.json = False
        handle_stream(plugin, streams, "best")
        self.assertEqual(console.msg.mock_calls, [call("{0}", stream.to_url())])
        self.assertEqual(console.msg_json.mock_calls, [])
        self.assertEqual(console.error.mock_calls, [])
        console.msg.mock_calls.clear()

        stream.to_url.side_effect = TypeError()
        handle_stream(plugin, streams, "best")
        self.assertEqual(console.msg.mock_calls, [])
        self.assertEqual(console.msg_json.mock_calls, [])
        self.assertEqual(console.exit.mock_calls, [call("The stream specified cannot be translated to a URL")])

    @patch("streamlink_cli.main.args", stream_url=True, stream=[], default_stream=[], retry_max=0, retry_streams=0)
    @patch("streamlink_cli.main.console", json=True)
    def test_handle_url_with_json_and_stream_url(self, console, args):
        stream = Mock()
        streams = dict(worst=Mock(), best=stream)
        plugin = Mock(FakePlugin(), module="fake", arguments=[], streams=Mock(return_value=streams))

        with patch("streamlink_cli.main.streamlink", resolve_url=Mock(return_value=plugin)):
            handle_url()
            self.assertEqual(console.msg.mock_calls, [])
            self.assertEqual(console.msg_json.mock_calls, [call(dict(plugin="fake", streams=streams))])
            self.assertEqual(console.error.mock_calls, [])
            console.msg_json.mock_calls.clear()

            console.json = False
            handle_url()
            self.assertEqual(console.msg.mock_calls, [call("{0}", stream.to_manifest_url())])
            self.assertEqual(console.msg_json.mock_calls, [])
            self.assertEqual(console.error.mock_calls, [])
            console.msg.mock_calls.clear()

            stream.to_manifest_url.side_effect = TypeError()
            handle_url()
            self.assertEqual(console.msg.mock_calls, [])
            self.assertEqual(console.msg_json.mock_calls, [])
            self.assertEqual(console.exit.mock_calls, [call("The stream specified cannot be translated to a URL")])
            console.exit.mock_calls.clear()

    def test_create_output_no_file_output_options(self):
        streamlink_cli.main.console = Mock()
        streamlink_cli.main.args = args = Mock()
        args.output = None
        args.stdout = None
        args.record = None
        args.record_and_pipe = None
        args.title = None
        args.player = "mpv"
        args.player_args = ""
        self.assertIsInstance(create_output(FakePlugin), PlayerOutput)

    def test_create_output_file_output(self):
        tmpfile = tempfile.NamedTemporaryFile()
        try:
            streamlink_cli.main.args = args = Mock()
            streamlink_cli.main.console = Mock()
            args.output = tmpfile.name
            self.assertTrue(os.path.exists(tmpfile.name))
            self.assertIsInstance(create_output(FakePlugin), FileOutput)
        finally:
            tmpfile.close()

    def test_create_output_stdout(self):
        streamlink_cli.main.console = Mock()
        streamlink_cli.main.args = args = Mock()
        args.output = None
        args.stdout = True
        self.assertIsInstance(create_output(FakePlugin), FileOutput)

    def test_create_output_record_and_pipe(self):
        tmpfile = tempfile.NamedTemporaryFile()
        try:
            streamlink_cli.main.console = Mock()
            streamlink_cli.main.args = args = Mock()
            args.output = None
            args.stdout = None
            args.record_and_pipe = tmpfile.name
            self.assertIsInstance(create_output(FakePlugin), FileOutput)
        finally:
            tmpfile.close()

    def test_create_output_record(self):
        tmpfile = tempfile.NamedTemporaryFile()
        try:
            streamlink_cli.main.console = Mock()
            streamlink_cli.main.args = args = Mock()
            args.output = None
            args.stdout = None
            args.record = tmpfile.name
            args.record_and_pipe = None
            args.title = None
            args.player = "mpv"
            args.player_args = ""
            args.player_fifo = None
            self.assertIsInstance(create_output(FakePlugin), PlayerOutput)
        finally:
            tmpfile.close()

    def test_create_output_record_and_other_file_output(self):
        streamlink_cli.main.console = console = Mock()
        streamlink_cli.main.args = args = Mock()
        console.exit = Mock()
        args.output = None
        args.stdout = True
        args.record_and_pipe = True
        create_output(FakePlugin)
        console.exit.assert_called_with("Cannot use record options with other file output options.")
