from datetime import datetime, timezone
from integrations.msty.personal import shared_news as s

def test_disabled_does_not_read(tmp_path):
    (tmp_path/'note.md').write_text('private draft')
    assert s.collect({'shared_news_folders':[{'path':str(tmp_path),'enabled':False}]},datetime.now(timezone.utc))==([],[])

def test_markdown_attributed_without_frontmatter(tmp_path):
    (tmp_path/'note.md').write_text('---\ntoken: never expose\n---\n# Local report\nUnverified observation.')
    entries,warnings=s.collect({'shared_news_folders':[{'path':str(tmp_path),'enabled':True,'label':'Colleague'}]},datetime.now(timezone.utc))
    assert len(entries)==1 and not warnings
    assert 'never expose' not in entries[0]['excerpt']
    assert entries[0]['source']=='Colleague' and len(entries[0]['sha256'])==64
    assert 'not the date' in s.render(entries,warnings)

def test_old_files_and_non_sources_excluded(tmp_path):
    import os
    (tmp_path/'old.md').write_text('old report');os.utime(tmp_path/'old.md',(0,0))
    (tmp_path/'secrets.json').write_text('not a news document')
    assert s.collect({'shared_news_folders':[{'path':str(tmp_path),'enabled':True}]},datetime.now(timezone.utc))==([],[])

def test_missing_folder_is_visible(tmp_path):
    entries,warnings=s.collect({'shared_news_folders':[{'path':str(tmp_path/'missing'),'enabled':True}]},datetime.now(timezone.utc))
    assert not entries and 'unavailable' in warnings[0]


def test_pdf_excerpt(tmp_path):
    import pytest
    pdf=pytest.importorskip('pypdf')
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer=pdf.PdfWriter();page=writer.add_blank_page(width=300,height=300)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    stream=DecodedStreamObject();stream.set_data(b'BT /F1 12 Tf 10 200 Td (Synthetic report excerpt) Tj ET')
    page[NameObject('/Contents')]=writer._add_object(stream)
    writer.write(tmp_path/'report.pdf')
    entries,warnings=s.collect({'shared_news_folders':[{'path':str(tmp_path),'enabled':True}]},datetime.now(timezone.utc))
    assert not warnings and 'Synthetic report excerpt' in entries[0]['excerpt']
