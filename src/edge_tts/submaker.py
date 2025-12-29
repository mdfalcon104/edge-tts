"""SubMaker module is used to generate subtitles from WordBoundary and SentenceBoundary events."""

from datetime import timedelta
from typing import List, Optional

from .srt_composer import Subtitle, compose
from .typing import TTSChunk


class SubMaker:
    """
    SubMaker is used to generate subtitles from WordBoundary and SentenceBoundary messages.
    Supports grouping words by line breaks in the original text.
    """

    def __init__(self, original_text: Optional[str] = None) -> None:
        self.cues: List[Subtitle] = []
        self.type: Optional[str] = None
        self.original_text = original_text
        self._line_groups: Optional[List[str]] = None
        self._current_line_index = 0
        self._current_line_words: List[Subtitle] = []
        self._all_words_buffer: List[Subtitle] = []  # Buffer all words first
        
        # Split original text by line breaks if provided
        if original_text:
            # Split by newlines and keep non-empty lines
            self._line_groups = [line.strip() for line in original_text.split('\n') if line.strip()]

    def feed(self, msg: TTSChunk) -> None:
        """
        Feed a WordBoundary or SentenceBoundary message to the SubMaker object.

        Args:
            msg (dict): The WordBoundary or SentenceBoundary message.

        Returns:
            None
        """
        if msg["type"] not in ("WordBoundary", "SentenceBoundary"):
            raise ValueError(
                "Invalid message type, expected 'WordBoundary' or 'SentenceBoundary'."
            )

        if self.type is None:
            self.type = msg["type"]
        elif self.type != msg["type"]:
            raise ValueError(
                f"Expected message type '{self.type}', but got '{msg['type']}'."
            )

        subtitle = Subtitle(
            index=len(self._all_words_buffer) + 1,
            start=timedelta(microseconds=msg["offset"] / 10),
            end=timedelta(microseconds=(msg["offset"] + msg["duration"]) / 10),
            content=msg["text"],
        )
        
        # Buffer all words - we'll group them in get_srt()
        self._all_words_buffer.append(subtitle)

    def get_srt(self) -> str:
        """
        Get the SRT formatted subtitles from the SubMaker object.

        Returns:
            str: The SRT formatted subtitles.
        """
        # If we have line groups and word boundaries, group words by lines
        if self._line_groups and self.type == "WordBoundary" and self._all_words_buffer:
            self._group_words_by_lines()
        else:
            # Default behavior: use individual words/sentences
            self.cues = self._all_words_buffer
        
        return compose(self.cues)

    def _group_words_by_lines(self) -> None:
        """Group buffered words into subtitle entries based on line breaks."""
        if not self._all_words_buffer or not self._line_groups:
            return
        
        # Create ONE subtitle with all text, preserving line breaks
        all_words_content = []
        word_index = 0
        
        for line_idx, line_text in enumerate(self._line_groups):
            line_words = []
            line_text_lower = line_text.lower()
            accumulated_text = ""
            
            # Collect words for this line
            while word_index < len(self._all_words_buffer):
                word = self._all_words_buffer[word_index]
                line_words.append(word.content)
                accumulated_text += (" " if accumulated_text else "") + word.content
                word_index += 1
                
                # Check if we've accumulated this line's text
                if accumulated_text.lower() == line_text_lower:
                    break
                if len(accumulated_text) >= len(line_text) and line_text_lower in accumulated_text.lower():
                    break
            
            # Add this line's words to the content
            all_words_content.append(" ".join(line_words))
        
        # Add any remaining words
        while word_index < len(self._all_words_buffer):
            all_words_content.append(self._all_words_buffer[word_index].content)
            word_index += 1
        
        # Create a single subtitle with line breaks preserved
        if self._all_words_buffer:
            combined = Subtitle(
                index=1,
                start=self._all_words_buffer[0].start,
                end=self._all_words_buffer[-1].end,
                content="\n".join(all_words_content),  # Preserve line breaks with \n
            )
            self.cues.append(combined)

    def __str__(self) -> str:
        return self.get_srt()


