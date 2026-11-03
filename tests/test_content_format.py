from pathlib import Path

import pytest

from assembler import assemble
from cli.commanding import CommandSession, build_usage_profile, command_assemble
from cli.main import parse_args
from core.models import Post
from writer import write


def test_cli_content_format_choices():
    assert parse_args([]).content_format == 'markdown'
    assert parse_args(['--content-format', 'html']).content_format == 'html'
    with pytest.raises(SystemExit):
        parse_args(['--content-format', 'invalid'])


@pytest.mark.parametrize('mode', ['per_post', 'book'])
@pytest.mark.parametrize('content_format', ['markdown', 'html'])
def test_output_content_and_excerpt(tmp_path: Path, mode: str, content_format: str):
    post = Post(title='Title', slug='title', content='<p>Main <strong>body</strong></p>',
                excerpt='<p>Short <em>summary</em></p>', frontmatter={'tag': 'example'})
    units = assemble([post], mode=mode, include_excerpt=True,
                     include_frontmatter=True, content_format=content_format)
    write(units, output_dir=tmp_path, mode=mode)
    content = (tmp_path / ('title.md' if mode == 'per_post' else 'book.md')).read_text()
    if content_format == 'html':
        assert '<p>Short <em>summary</em></p>' in content
        assert '<p>Main <strong>body</strong></p>' in content
    else:
        assert 'Short *summary*' in content
        assert 'Main **body**' in content
    assert content.index('Short') < content.index('Main')
    assert 'tag: example' in content


def test_interactive_session_stores_format():
    session = CommandSession(posts=[Post(title='Title', content='<b>body</b>')], mode='per_post')
    command_assemble(session, content_format='html', prompt_for_parameters=False)
    assert session.units[0].content == '<b>body</b>'
    assert build_usage_profile(session)['content_format'] == 'html'


def test_invalid_format_is_rejected():
    with pytest.raises(ValueError, match='Unsupported content format'):
        assemble([], content_format='invalid')
