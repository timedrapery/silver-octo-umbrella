import webbrowser
from urllib.parse import quote_plus

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.models.case import Case, SavedSearch, SearchIntent, SearchProvider
from app.services.case_service import CaseService
from app.services.search_builder_service import SearchBuildRequest, SearchBuildResult, SearchBuilderService


class SearchBuilderPanel(QWidget):
    status_changed = Signal(str)

    def __init__(
        self,
        case_service: CaseService,
        search_builder_service: SearchBuilderService,
        parent=None,
    ):
        super().__init__(parent)
        self.case_service = case_service
        self.search_builder_service = search_builder_service
        self.current_case: Case | None = None
        self.current_result: SearchBuildResult | None = None
        self._saved_searches: list[SavedSearch] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        summary_row = QHBoxLayout()
        self.search_count_label = QLabel("Saved Searches: 0")
        self.linked_target_count_label = QLabel("Linked To Targets: 0")
        self.last_search_label = QLabel("Last Search: -")
        for label in [
            self.search_count_label,
            self.linked_target_count_label,
            self.last_search_label,
        ]:
            label.setStyleSheet("padding: 4px 8px; border: 1px solid #444; border-radius: 4px;")
            summary_row.addWidget(label)
        summary_row.addStretch()
        layout.addLayout(summary_row)

        recipe_group = QGroupBox("Guided Search Setup")
        recipe_layout = QGridLayout(recipe_group)

        self.recipe_combo = QComboBox()
        self.recipe_combo.addItem("Custom", "custom")
        for recipe in self.search_builder_service.list_recipes():
            self.recipe_combo.addItem(recipe.name, recipe.id)
        self.recipe_combo.currentIndexChanged.connect(self._on_recipe_selected)

        self.intent_combo = QComboBox()
        for intent in SearchIntent:
            self.intent_combo.addItem(intent.value.replace("_", " ").title(), intent.value)

        self.target_combo = QComboBox()
        self.target_combo.addItem("No Target Association", None)
        self.target_combo.currentIndexChanged.connect(self._on_target_selected)

        self.target_text_input = QLineEdit()
        self.target_text_input.setPlaceholderText("Target text (person, username, domain, email, company, etc.)")

        self.search_title_input = QLineEdit()
        self.search_title_input.setPlaceholderText("Search title (e.g., Public docs - example.com)")

        self.exact_phrase_input = QLineEdit()
        self.exact_phrase_input.setPlaceholderText("Exact phrase")

        self.all_terms_input = QLineEdit()
        self.all_terms_input.setPlaceholderText("All terms (comma or space separated)")

        self.any_terms_input = QLineEdit()
        self.any_terms_input.setPlaceholderText("Any terms (comma or space separated)")

        self.exclude_terms_input = QLineEdit()
        self.exclude_terms_input.setPlaceholderText("Excluded terms (comma or space separated)")

        self.site_input = QLineEdit()
        self.site_input.setPlaceholderText("Site/domain restriction (example.com)")

        self.filetype_input = QLineEdit()
        self.filetype_input.setPlaceholderText("Filetype (pdf, docx, xlsx, etc.)")

        self.intitle_input = QLineEdit()
        self.intitle_input.setPlaceholderText("Title terms (comma or space separated)")

        self.inurl_input = QLineEdit()
        self.inurl_input.setPlaceholderText("URL terms (comma or space separated)")

        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("Tags (comma separated)")

        self.note_input = QLineEdit()
        self.note_input.setPlaceholderText("Analyst note (purpose/context)")

        row = 0
        recipe_layout.addWidget(QLabel("Recipe"), row, 0)
        recipe_layout.addWidget(self.recipe_combo, row, 1)
        recipe_layout.addWidget(QLabel("Intent"), row, 2)
        recipe_layout.addWidget(self.intent_combo, row, 3)

        row += 1
        recipe_layout.addWidget(QLabel("Target"), row, 0)
        recipe_layout.addWidget(self.target_combo, row, 1)
        recipe_layout.addWidget(QLabel("Target Text"), row, 2)
        recipe_layout.addWidget(self.target_text_input, row, 3)

        row += 1
        recipe_layout.addWidget(QLabel("Title"), row, 0)
        recipe_layout.addWidget(self.search_title_input, row, 1, 1, 3)

        row += 1
        recipe_layout.addWidget(QLabel("Exact Phrase"), row, 0)
        recipe_layout.addWidget(self.exact_phrase_input, row, 1)
        recipe_layout.addWidget(QLabel("All Terms"), row, 2)
        recipe_layout.addWidget(self.all_terms_input, row, 3)

        row += 1
        recipe_layout.addWidget(QLabel("Any Terms"), row, 0)
        recipe_layout.addWidget(self.any_terms_input, row, 1)
        recipe_layout.addWidget(QLabel("Excluded Terms"), row, 2)
        recipe_layout.addWidget(self.exclude_terms_input, row, 3)

        row += 1
        recipe_layout.addWidget(QLabel("Site"), row, 0)
        recipe_layout.addWidget(self.site_input, row, 1)
        recipe_layout.addWidget(QLabel("Filetype"), row, 2)
        recipe_layout.addWidget(self.filetype_input, row, 3)

        row += 1
        recipe_layout.addWidget(QLabel("Title Focus"), row, 0)
        recipe_layout.addWidget(self.intitle_input, row, 1)
        recipe_layout.addWidget(QLabel("URL Focus"), row, 2)
        recipe_layout.addWidget(self.inurl_input, row, 3)

        row += 1
        recipe_layout.addWidget(QLabel("Tags"), row, 0)
        recipe_layout.addWidget(self.tags_input, row, 1)
        recipe_layout.addWidget(QLabel("Analyst Note"), row, 2)
        recipe_layout.addWidget(self.note_input, row, 3)

        layout.addWidget(recipe_group)

        action_row = QHBoxLayout()
        self.generate_btn = QPushButton("Generate Query")
        self.launch_btn = QPushButton("Launch In Browser")
        self.save_btn = QPushButton("Save Search")
        self.copy_btn = QPushButton("Copy Query")
        self.generate_btn.clicked.connect(self._generate_query)
        self.launch_btn.clicked.connect(self._launch_query)
        self.save_btn.clicked.connect(self._save_search)
        self.copy_btn.clicked.connect(self._copy_query)
        action_row.addWidget(self.generate_btn)
        action_row.addWidget(self.launch_btn)
        action_row.addWidget(self.save_btn)
        action_row.addWidget(self.copy_btn)
        action_row.addStretch()
        layout.addLayout(action_row)

        preview_group = QGroupBox("Query Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.query_preview = QTextEdit()
        self.query_preview.setReadOnly(True)
        self.query_preview.setMaximumHeight(80)
        self.explanation_preview = QTextEdit()
        self.explanation_preview.setReadOnly(True)
        self.explanation_preview.setMaximumHeight(110)
        preview_layout.addWidget(QLabel("Generated Query"))
        preview_layout.addWidget(self.query_preview)
        preview_layout.addWidget(QLabel("Plain-Language Explanation"))
        preview_layout.addWidget(self.explanation_preview)
        layout.addWidget(preview_group)

        saved_group = QGroupBox("Saved Searches")
        saved_layout = QVBoxLayout(saved_group)
        self.saved_table = QTableWidget(0, 5)
        self.saved_table.setHorizontalHeaderLabels(["Title", "Intent", "Target", "Created", "Provider"])
        self.saved_table.horizontalHeader().setStretchLastSection(True)
        self.saved_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.saved_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.saved_table.itemSelectionChanged.connect(self._load_selected_preview)
        saved_layout.addWidget(self.saved_table)

        saved_actions = QHBoxLayout()
        self.load_btn = QPushButton("Load Selected")
        self.duplicate_btn = QPushButton("Duplicate")
        self.delete_btn = QPushButton("Delete")
        self.load_btn.clicked.connect(self._load_selected_to_form)
        self.duplicate_btn.clicked.connect(self._duplicate_selected)
        self.delete_btn.clicked.connect(self._delete_selected)
        saved_actions.addWidget(self.load_btn)
        saved_actions.addWidget(self.duplicate_btn)
        saved_actions.addWidget(self.delete_btn)
        saved_actions.addStretch()
        saved_layout.addLayout(saved_actions)

        layout.addWidget(saved_group)

    def load_case(self, case: Case):
        self.current_case = case
        self._refresh_targets(case)
        self._refresh_saved_searches()

    def _refresh_targets(self, case: Case) -> None:
        previous = self.target_combo.currentData()
        self.target_combo.blockSignals(True)
        self.target_combo.clear()
        self.target_combo.addItem("No Target Association", None)
        for target in case.targets:
            self.target_combo.addItem(f"[{target.type.value}] {target.value}", target.id)
        idx = self.target_combo.findData(previous)
        self.target_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.target_combo.blockSignals(False)

    def _refresh_saved_searches(self) -> None:
        if self.current_case is None:
            return

        self._saved_searches = self.case_service.list_saved_searches(self.current_case.id)
        self.saved_table.setRowCount(0)

        target_map = {target.id: f"[{target.type.value}] {target.value}" for target in self.current_case.targets}

        for search in self._saved_searches:
            row = self.saved_table.rowCount()
            self.saved_table.insertRow(row)
            self.saved_table.setItem(row, 0, QTableWidgetItem(search.title))
            self.saved_table.setItem(row, 1, QTableWidgetItem(search.intent.value))
            self.saved_table.setItem(
                row,
                2,
                QTableWidgetItem(target_map.get(search.target_id, "-")),
            )
            self.saved_table.setItem(
                row,
                3,
                QTableWidgetItem(search.created_at.strftime("%Y-%m-%d %H:%M")),
            )
            self.saved_table.setItem(row, 4, QTableWidgetItem(search.provider.value))
            self.saved_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, search.id)

        summary = self.case_service.get_case_search_summary(self.current_case.id)
        self.search_count_label.setText(f"Saved Searches: {summary.total}")
        self.linked_target_count_label.setText(f"Linked To Targets: {summary.linked_targets}")
        last = summary.last_created_at.strftime("%Y-%m-%d %H:%M") if summary.last_created_at else "-"
        self.last_search_label.setText(f"Last Search: {last}")

    def _on_target_selected(self) -> None:
        if self.current_case is None:
            return
        selected_target_id = self.target_combo.currentData()
        if not selected_target_id:
            return
        for target in self.current_case.targets:
            if target.id == selected_target_id:
                self.target_text_input.setText(target.value)
                return

    def _on_recipe_selected(self) -> None:
        recipe_id = self.recipe_combo.currentData()
        if not recipe_id or recipe_id == "custom":
            return
        recipe = self.search_builder_service.get_recipe(recipe_id)
        if recipe is None:
            return

        idx = self.intent_combo.findData(recipe.intent.value)
        self.intent_combo.setCurrentIndex(idx if idx >= 0 else 0)
        if recipe.suggested_site and not self.site_input.text().strip():
            self.site_input.setText(recipe.suggested_site)
        if recipe.suggested_filetype and not self.filetype_input.text().strip():
            self.filetype_input.setText(recipe.suggested_filetype)
        if recipe.suggested_all_terms and not self.all_terms_input.text().strip():
            self.all_terms_input.setText(", ".join(recipe.suggested_all_terms))
        if recipe.suggested_excluded_terms and not self.exclude_terms_input.text().strip():
            self.exclude_terms_input.setText(", ".join(recipe.suggested_excluded_terms))

    def _build_request(self) -> SearchBuildRequest:
        return SearchBuildRequest(
            provider=SearchProvider.GOOGLE,
            intent=SearchIntent(self.intent_combo.currentData()),
            target_value=self.target_text_input.text().strip(),
            exact_phrase=self.exact_phrase_input.text().strip(),
            all_terms=self.search_builder_service.parse_terms(self.all_terms_input.text()),
            any_terms=self.search_builder_service.parse_terms(self.any_terms_input.text()),
            excluded_terms=self.search_builder_service.parse_terms(self.exclude_terms_input.text()),
            site=self.site_input.text().strip(),
            filetype=self.filetype_input.text().strip(),
            in_title_terms=self.search_builder_service.parse_terms(self.intitle_input.text()),
            in_url_terms=self.search_builder_service.parse_terms(self.inurl_input.text()),
        )

    def _generate_query(self) -> None:
        try:
            request = self._build_request()
            self.current_result = self.search_builder_service.build_query(request)
            self.query_preview.setPlainText(self.current_result.query)
            self.explanation_preview.setPlainText(self.current_result.explanation)
            self.status_changed.emit("Search query generated")
        except ValueError as exc:
            self.status_changed.emit(str(exc))

    def _launch_query(self) -> None:
        if self.current_result is None:
            self._generate_query()
        if self.current_result is None:
            return
        webbrowser.open(self.current_result.launch_url)
        self.status_changed.emit("Opened search in browser")

    def _copy_query(self) -> None:
        query = self.query_preview.toPlainText().strip()
        if not query:
            self.status_changed.emit("No query to copy")
            return
        clipboard = QApplication.clipboard()
        clipboard.setText(query)
        self.status_changed.emit("Query copied to clipboard")

    def _save_search(self) -> None:
        if self.current_case is None:
            self.status_changed.emit("Select a case before saving a search")
            return

        if self.current_result is None:
            self._generate_query()
        if self.current_result is None:
            return

        title = self.search_title_input.text().strip() or "Untitled Search"
        tags = [tag.strip() for tag in self.tags_input.text().split(",") if tag.strip()]

        self.case_service.create_saved_search(
            case_id=self.current_case.id,
            title=title,
            query=self.current_result.query,
            explanation=self.current_result.explanation,
            intent=SearchIntent(self.intent_combo.currentData()),
            provider=SearchProvider.GOOGLE,
            target_id=self.target_combo.currentData(),
            tags=tags,
            analyst_note=self.note_input.text().strip(),
        )

        self.current_case = self.case_service.get_case(self.current_case.id)
        self._refresh_saved_searches()
        self.status_changed.emit("Saved search to case")

    def _selected_saved_search(self) -> SavedSearch | None:
        row = self.saved_table.currentRow()
        if row < 0:
            return None
        item = self.saved_table.item(row, 0)
        if item is None:
            return None
        search_id = item.data(Qt.ItemDataRole.UserRole)
        for search in self._saved_searches:
            if search.id == search_id:
                return search
        return None

    def _load_selected_preview(self) -> None:
        search = self._selected_saved_search()
        if search is None:
            return
        self.query_preview.setPlainText(search.query)
        self.explanation_preview.setPlainText(search.explanation)

    def _load_selected_to_form(self) -> None:
        search = self._selected_saved_search()
        if search is None:
            self.status_changed.emit("Select a saved search first")
            return

        self.search_title_input.setText(search.title)
        self.note_input.setText(search.analyst_note)
        self.tags_input.setText(", ".join(search.tags))
        intent_idx = self.intent_combo.findData(search.intent.value)
        self.intent_combo.setCurrentIndex(intent_idx if intent_idx >= 0 else 0)
        target_idx = self.target_combo.findData(search.target_id)
        self.target_combo.setCurrentIndex(target_idx if target_idx >= 0 else 0)
        self.query_preview.setPlainText(search.query)
        self.explanation_preview.setPlainText(search.explanation)
        self.current_result = SearchBuildResult(
            query=search.query,
            explanation=search.explanation,
            launch_url="https://www.google.com/search?q=" + quote_plus(search.query),
        )
        self.status_changed.emit("Loaded saved search into builder")

    def _duplicate_selected(self) -> None:
        search = self._selected_saved_search()
        if search is None:
            self.status_changed.emit("Select a saved search first")
            return

        duplicate_title = f"{search.title} (Copy)"
        self.case_service.create_saved_search(
            case_id=search.case_id,
            title=duplicate_title,
            query=search.query,
            explanation=search.explanation,
            intent=search.intent,
            provider=search.provider,
            target_id=search.target_id,
            tags=search.tags,
            analyst_note=search.analyst_note,
        )

        self.current_case = self.case_service.get_case(search.case_id)
        self._refresh_saved_searches()
        self.status_changed.emit("Saved search duplicated")

    def _delete_selected(self) -> None:
        search = self._selected_saved_search()
        if search is None:
            self.status_changed.emit("Select a saved search first")
            return

        self.case_service.delete_saved_search(search.case_id, search.id)
        self.current_case = self.case_service.get_case(search.case_id)
        self._refresh_saved_searches()
        self.status_changed.emit("Saved search deleted")

    def seed_email_pivot(self, email_value: str) -> None:
        idx = self.intent_combo.findData(SearchIntent.EMAIL_MENTION.value)
        self.intent_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.target_text_input.setText(email_value)
        self.search_title_input.setText(f"Email Pivot - {email_value}")
        self.exact_phrase_input.setText(email_value)
        self.all_terms_input.setText("breach, leak, profile")
        self.exclude_terms_input.setText("example")
        self._generate_query()

    def seed_username_pivot(self, username_value: str) -> None:
        idx = self.intent_combo.findData(SearchIntent.USERNAME_FOOTPRINT.value)
        self.intent_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.target_text_input.setText(username_value)
        self.search_title_input.setText(f"Username Pivot - {username_value}")
        self.exact_phrase_input.setText(username_value)
        self.all_terms_input.setText("profile, account")
        self._generate_query()
