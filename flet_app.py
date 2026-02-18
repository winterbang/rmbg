import flet as ft
import threading
import tempfile
import shutil
import time
import base64
import io
from pathlib import Path
from typing import List, Dict
from PIL import Image
import uvicorn
from app.core.model import BackgroundRemover
from app.core import config
from app.api import endpoints
from app.main import app as fastapi_app

# --- Global State ---
remover = None
api_server_started = False
api_server_instance = None
processed_results = {}  # original_path -> temp_path
TEMP_DIR = tempfile.mkdtemp()

# --- Color Scheme ---
class Colors:
    BG_PRIMARY = "#1a2332"
    BG_SECONDARY = "#232d3f"
    BG_CARD = "#2a3447"
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#8b95a5"
    BORDER = "#2d3748"
    ACCENT = "#2196f3"
    SUCCESS = "#4caf50"
    ERROR = "#f44336"
    WARNING = "#ff9800"

def main(page: ft.Page):
    page.title = "NoBG - Background Remover"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = Colors.BG_PRIMARY
    page.padding = 0
    page.window.width = 1100
    page.window.height = 750
    page.window.title_bar_hidden = True
    page.window.title_bar_buttons_hidden = False
    
    # --- State ---
    files_to_process = []
    view_mode = "grid"  # "grid" or "list"
    current_view = "loading"  # "loading", "empty", "batch"
    
    # --- Loading Screen ---
    loading_progress = ft.ProgressBar(
        width=300,
        color=Colors.ACCENT,
        bgcolor=Colors.BORDER,
        value=0
    )
    
    loading_text = ft.Text(
        "Loading neural networks...",
        size=14,
        color=Colors.TEXT_SECONDARY
    )
    
    loading_percentage = ft.Text(
        "0%",
        size=14,
        color=Colors.TEXT_SECONDARY,
        weight=ft.FontWeight.BOLD
    )
    
    loading_screen = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Image(src="icon.png", width=80, height=80, fit=ft.ImageFit.CONTAIN),
                                    ft.Text(
                                        "NoBG",
                                        size=32,
                                        weight=ft.FontWeight.BOLD,
                                        color=Colors.TEXT_PRIMARY
                                    ),
                                    ft.Text(
                                        "Pro Background Remover",
                                        size=14,
                                        color=Colors.TEXT_SECONDARY
                                    ),
                                    ft.Container(height=30),
                                    loading_progress,
                                    ft.Row(
                                        [loading_text, loading_percentage],
                                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                        width=300
                                    ),
                                    ft.Container(height=20),
                                    ft.Text(
                                        "Version 2.4.0 • Built with Flet",
                                        size=11,
                                        color=Colors.TEXT_SECONDARY,
                                        opacity=0.6
                                    ),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=10
                            ),
                            padding=40,
                            bgcolor=Colors.BG_SECONDARY,
                            border_radius=12,
                            width=400,
                            shadow=ft.BoxShadow(
                                spread_radius=1,
                                blur_radius=15,
                                color=ft.colors.with_opacity(0.3, "#000000")
                            )
                        )
                    ],
                    alignment=ft.MainAxisAlignment.CENTER
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        ),
        expand=True,
        visible=True
    )
    
    # --- Model Loading Thread ---
    def load_model_thread():
        global remover
        try:
            def update_progress(progress: float, message: str):
                """Callback to update loading UI"""
                loading_progress.value = progress
                loading_percentage.value = f"{int(progress * 100)}%"
                loading_text.value = message
                page.update()
            
            # Initialize with real progress tracking
            remover = BackgroundRemover(progress_callback=update_progress)
            
            time.sleep(0.5)  # Brief pause to show "Ready!" message
            
            # Switch to empty view
            loading_screen.visible = False
            main_container.visible = True
            empty_view.visible = True
            page.update()
            
            
        except Exception as e:
            loading_text.value = f"Error: {str(e)}"
            loading_text.color = Colors.ERROR
            page.update()
            
    # --- Alert System ---
    alert_view = ft.Container(
        right=-400,  # Start off-screen
        top=20,
        width=320,
        bgcolor=Colors.BG_SECONDARY,
        border_radius=8,
        padding=16,
        shadow=ft.BoxShadow(
            spread_radius=1,
            blur_radius=15,
            color=ft.colors.with_opacity(0.3, "#000000")
        ),
        animate_position=ft.animation.Animation(400, ft.AnimationCurve.EASE_OUT_CUBIC),
        content=ft.Row(
            [
                ft.Icon(name=ft.icons.CHECK_CIRCLE, color=Colors.SUCCESS),
                ft.Text("Message", size=14, weight=ft.FontWeight.W_500, color=Colors.TEXT_PRIMARY, expand=True)
            ],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        ),
        visible=True
    )
    
    page.overlay.append(alert_view)
    
    def show_alert(message, type="success"):
        color = {
            "success": Colors.SUCCESS,
            "error": Colors.ERROR,
            "info": Colors.ACCENT,
            "warning": Colors.WARNING
        }.get(type, Colors.ACCENT)
        
        icon = {
            "success": ft.icons.CHECK_CIRCLE,
            "error": ft.icons.ERROR_OUTLINE,
            "info": ft.icons.INFO_OUTLINE,
            "warning": ft.icons.WARNING_AMBER
        }.get(type, ft.icons.INFO_OUTLINE)
        
        # Update content safely
        alert_view.content.controls[0].name = icon
        alert_view.content.controls[0].color = color
        alert_view.content.controls[1].value = message
        alert_view.border = ft.border.only(left=ft.BorderSide(4, color))
        alert_view.right = 20
        alert_view.update()
        
        def hide():
            import time
            time.sleep(3)
            alert_view.right = -400
            alert_view.update()
            
        import threading
        threading.Thread(target=hide, daemon=True).start()
    
    # --- Top Navigation Bar ---
    api_switch = ft.Switch(
        label="Enable API",
        height=24,
        value=False,
        active_color=Colors.ACCENT,
        label_style=ft.TextStyle(color=Colors.TEXT_SECONDARY, size=13)
    )
    
    def toggle_api(e):
        global api_server_started, api_server_instance
        
        if e.control.value:
            # Start API
            if not remover:
                show_alert("Model not ready", "warning")
                e.control.value = False
                page.update()
                return
            
            endpoints.bg_remover = remover
            
            def run_server():
                global api_server_instance
                config_obj = uvicorn.Config(fastapi_app, host="0.0.0.0", port=8000, log_level="info")
                api_server_instance = uvicorn.Server(config_obj)
                api_server_instance.run()
            
            threading.Thread(target=run_server, daemon=True).start()
            api_server_started = True
            
            show_alert("API Server started on port 8000", "success")
        else:
            # Stop API
            if api_server_instance:
                api_server_instance.should_exit = True
            api_server_started = False
            
            show_alert("API Server stopped", "warning")
        
        page.update()
    
    api_switch.on_change = toggle_api
    
    # Batch control buttons (defined early for use in top_nav)
    def toggle_view_mode(e):
        nonlocal view_mode
        view_mode = "grid" if view_mode == "list" else "list"
        grid_btn.icon = ft.icons.VIEW_LIST if view_mode == "grid" else ft.icons.GRID_VIEW
        update_file_list()
    
    grid_btn = ft.IconButton(
        icon=ft.icons.VIEW_LIST,
        icon_color=Colors.TEXT_SECONDARY,
        tooltip="Toggle View",
        on_click=toggle_view_mode,
        visible=False  # Hidden by default
    )
    
    def clear_all(e):
        nonlocal files_to_process
        files_to_process = []
        batch_view.visible = False
        empty_view.visible = True
        grid_btn.visible = False
        clear_btn.visible = False
        page.update()
    
    clear_btn = ft.TextButton(
        "Clear",
        icon=ft.icons.CLEANING_SERVICES,
        style=ft.ButtonStyle(
            color=Colors.TEXT_SECONDARY
        ),
        height=16,
        on_click=clear_all,
        visible=False  # Hidden by default
    )
    
    top_nav = ft.Container(
        content=ft.Row(
            [
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Image(src="icon.png", width=28, height=28, fit=ft.ImageFit.CONTAIN),
                            border_radius=8,
                            padding=0,
                            width=40,
                            height=40,
                            alignment=ft.alignment.center
                        ),
                        ft.Text(
                            "NoBG",
                            size=16,
                            weight=ft.FontWeight.W_500,
                            color=Colors.TEXT_PRIMARY
                        )
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                ),
                ft.Row(
                    [
                        grid_btn,
                        clear_btn,
                        api_switch
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        ),
        padding=ft.padding.only(left=80, right=24, top=0, bottom=0),
        bgcolor=Colors.BG_SECONDARY,
        border=ft.border.only(bottom=ft.BorderSide(1, Colors.BORDER))
    )
    
    # --- File Pickers ---
    def on_file_picker_result(e: ft.FilePickerResultEvent):
        if e.files:
            add_files([f.path for f in e.files])
    
    def on_folder_picker_result(e: ft.FilePickerResultEvent):
        if e.path:
            folder_path = Path(e.path)
            image_files = []
            for ext in ['*.png', '*.jpg', '*.jpeg', '*.webp', '*.bmp']:
                image_files.extend(folder_path.glob(ext))
            add_files([str(f) for f in image_files])
    
    file_picker = ft.FilePicker(on_result=on_file_picker_result)
    folder_picker = ft.FilePicker(on_result=on_folder_picker_result)
    page.overlay.extend([file_picker, folder_picker])
    
    def generate_thumbnail(image_path: str, size=(100, 100)):
        """Generate base64 encoded thumbnail"""
        try:
            img = Image.open(image_path)
            img.thumbnail(size, Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            return base64.b64encode(buffer.getvalue()).decode()
        except Exception as e:
            print(f"Thumbnail error: {e}")
            return None
    
    def add_files(paths: List[str]):
        nonlocal files_to_process
        for path in paths:
            if path not in [f['path'] for f in files_to_process]:
                thumb = generate_thumbnail(path)
                files_to_process.append({
                    'path': path,
                    'name': Path(path).name,
                    'size': Path(path).stat().st_size,
                    'status': 'pending',  # pending, processing, done, error
                    'result_path': None,
                    'thumbnail': thumb
                })
        
        # Switch to batch view
        empty_view.visible = False
        batch_view.visible = True
        grid_btn.visible = True
        clear_btn.visible = True
        update_file_list()
        update_progress_ui()
        page.update()
    
    # --- Empty View (Drag & Drop) ---
    browse_btn = ft.Container(
        content=ft.ElevatedButton(
            content=ft.Row(
                [
                    ft.Icon(ft.icons.FOLDER_OPEN, size=18),
                    ft.Text("Browse Files", size=14)
                ],
                spacing=8,
                tight=True
            ),
            style=ft.ButtonStyle(
                bgcolor=Colors.ACCENT,
                color=Colors.TEXT_PRIMARY,
                padding=ft.padding.symmetric(horizontal=24, vertical=16),
                shape=ft.RoundedRectangleBorder(radius=8)
            ),
            on_click=lambda _: file_picker.pick_files(
                allow_multiple=True,
                allowed_extensions=["png", "jpg", "jpeg", "webp", "bmp"]
            )
        ),
        width=200
    )
    
    empty_view = ft.Container(
        content=ft.GestureDetector(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(
                            ft.icons.CLOUD_UPLOAD_OUTLINED,
                            size=64,
                            color=Colors.ACCENT
                        ),
                        ft.Container(height=16),
                        ft.Text(
                            "Upload an image to remove background",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color=Colors.TEXT_PRIMARY
                        ),
                        ft.Container(height=8),
                        ft.Text(
                            "Drag and drop your file here, or click to browse your computer.",
                            size=14,
                            color=Colors.TEXT_SECONDARY
                        ),
                        ft.Container(height=24),
                        browse_btn,
                        ft.Container(height=32),
                        ft.Row(
                            [
                                ft.Icon(ft.icons.CHECK_CIRCLE_OUTLINE, size=16, color=Colors.SUCCESS),
                                ft.Text("PNG, JPG, WEBP", size=12, color=Colors.TEXT_SECONDARY),
                                ft.Text("•", size=12, color=Colors.TEXT_SECONDARY),
                                ft.Text("Max 10MB", size=12, color=Colors.TEXT_SECONDARY)
                            ],
                            spacing=8,
                            alignment=ft.MainAxisAlignment.CENTER
                        )
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=0
                ),
                padding=80,
                border=ft.border.all(2, Colors.BORDER),
                border_radius=12,
                # Dashed border effect
                # Note: Flet doesn't support dashed borders natively, using solid as fallback
            ),
            on_double_tap=lambda _: file_picker.pick_files(
                allow_multiple=True,
                allowed_extensions=["png", "jpg", "jpeg", "webp", "bmp"]
            )
        ),
        padding=40,
        expand=True,
        visible=False
    )
    
    # --- Batch View ---
    file_list_container = ft.Container(expand=True)
    
    def update_file_list():
        if view_mode == "list":
            # List View Implementation
            list_controls = []
            
            # Table header
            list_controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Text("FILE NAME", size=11, weight=ft.FontWeight.BOLD, color=Colors.TEXT_SECONDARY, expand=3),
                            ft.Text("STATUS", size=11, weight=ft.FontWeight.BOLD, color=Colors.TEXT_SECONDARY, expand=1),
                            ft.Text("SIZE/FORMAT", size=11, weight=ft.FontWeight.BOLD, color=Colors.TEXT_SECONDARY, expand=1),
                            ft.Text("ACTIONS", size=11, weight=ft.FontWeight.BOLD, color=Colors.TEXT_SECONDARY, expand=1),
                        ]
                    ),
                    padding=ft.padding.symmetric(horizontal=16, vertical=8),
                    bgcolor=Colors.BG_SECONDARY
                )
            )
            
            # File rows
            for file_data in files_to_process:
                status_color = {
                    'pending': Colors.TEXT_SECONDARY,
                    'processing': Colors.WARNING,
                    'done': Colors.SUCCESS,
                    'error': Colors.ERROR
                }.get(file_data['status'], Colors.TEXT_SECONDARY)
                
                status_text = {
                    'pending': 'Pending',
                    'processing': 'Processing',
                    'done': 'Done',
                    'error': 'Error'
                }.get(file_data['status'], 'Unknown')
                
                file_size_mb = file_data['size'] / (1024 * 1024)
                file_ext = Path(file_data['name']).suffix.upper()[1:]
                
                list_controls.append(
                    ft.GestureDetector(
                        content=ft.Container(
                            content=ft.Row(
                                [
                                    ft.Row(
                                        [
                                            # Show real thumbnail if available
                                            ft.Container(
                                                content=ft.Image(
                                                    src_base64=file_data['thumbnail'],
                                                    width=40,
                                                    height=40,
                                                    fit=ft.ImageFit.COVER
                                                ) if file_data.get('thumbnail') else ft.Icon(ft.icons.IMAGE, size=20, color=Colors.TEXT_SECONDARY),
                                                width=40,
                                                height=40,
                                                bgcolor=Colors.BG_CARD,
                                                border_radius=6,
                                                clip_behavior=ft.ClipBehavior.HARD_EDGE
                                            ),
                                            ft.Column(
                                                [
                                                    ft.Text(file_data['name'], size=13, color=Colors.TEXT_PRIMARY),
                                                    ft.Text(f"Original", size=11, color=Colors.TEXT_SECONDARY)
                                                ],
                                                spacing=2
                                            )
                                        ],
                                        spacing=12,
                                        expand=3
                                    ),
                                    ft.Container(
                                        content=ft.Text(status_text, size=12, color=status_color),
                                        expand=1
                                    ),
                                    ft.Text(f"{file_size_mb:.1f} MB • {file_ext}", size=12, color=Colors.TEXT_SECONDARY, expand=1),
                                    ft.Row(
                                        [
                                            ft.IconButton(
                                                icon=ft.icons.DOWNLOAD,
                                                icon_size=18,
                                                icon_color=Colors.ACCENT,
                                                tooltip="Save",
                                                visible=file_data['status'] == 'done',
                                                on_click=lambda e, f=file_data: save_single_file(f)
                                            ),
                                            ft.IconButton(
                                                icon=ft.icons.DELETE_OUTLINE,
                                                icon_size=18,
                                                icon_color=Colors.ERROR,
                                                tooltip="Delete",
                                                on_click=lambda e, f=file_data: delete_single_file(f)
                                            )
                                        ],
                                        spacing=4,
                                        expand=1
                                    )
                                ]
                            ),
                            padding=ft.padding.symmetric(horizontal=16, vertical=12),
                            bgcolor=Colors.BG_SECONDARY,
                            border_radius=8
                        ),
                        on_secondary_tap_down=lambda e, f=file_data: show_context_menu(e, f)
                    )
                )
            
            file_list_container.content = ft.Column(list_controls, spacing=8, scroll=ft.ScrollMode.AUTO)
            
        else:
            # Grid view - Reference design style
            grid_items = []
            for file_data in files_to_process:
                status = file_data['status']
                file_size_mb = file_data['size'] / (1024 * 1024)
                file_ext = Path(file_data['name']).suffix.upper()[1:]
                
                # Status badge configuration
                status_config = {
                    'pending': {'text': 'PENDING', 'color': Colors.WARNING, 'bg': '#3D3D00'},
                    'processing': {'text': 'PROCESSING', 'color': Colors.WARNING, 'bg': '#3D3D00'},
                    'done': {'text': 'DONE', 'color': Colors.SUCCESS, 'bg': '#003D00'},
                    'error': {'text': 'FAILED', 'color': Colors.ERROR, 'bg': '#3D0000'}
                }.get(status, {'text': 'UNKNOWN', 'color': Colors.TEXT_SECONDARY, 'bg': '#2D2D2D'})
                
                # Build card
                card_content = [
                    # Image with status badge overlay
                    ft.Stack(
                        alignment=ft.alignment.center,
                        width=180,
                        height=180,
                        controls=[
                            # Main image
                            ft.Container(
                                content=ft.Image(
                                    src_base64=file_data['thumbnail'],
                                    width=180,
                                    height=180,
                                    fit=ft.ImageFit.CONTAIN
                                ) if file_data.get('thumbnail') else ft.Container(
                                    content=ft.Icon(ft.icons.IMAGE, size=48, color=Colors.TEXT_SECONDARY),
                                    alignment=ft.alignment.center
                                ),
                                width=180,
                                height=180,
                                bgcolor=Colors.BG_CARD,
                                border_radius=8,
                                clip_behavior=ft.ClipBehavior.HARD_EDGE
                            ),
                            # Status badge (top-right)
                            ft.Container(
                                content=ft.Text(
                                    status_config['text'],
                                    size=10,
                                    weight=ft.FontWeight.BOLD,
                                    color=status_config['color']
                                ),
                                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                                bgcolor=status_config['bg'],
                                border_radius=4,
                                right=8,
                                top=8
                            ),
                            # Processing spinner
                            ft.Container(
                                content=ft.ProgressRing(
                                    width=40,
                                    height=40,
                                    stroke_width=3,
                                    color=Colors.ACCENT
                                ),
                                alignment=ft.alignment.center,
                                visible=status == 'processing'
                            ) if status == 'processing' else ft.Container(),
                            # Error icon
                            ft.Container(
                                content=ft.Icon(
                                    ft.icons.ERROR_OUTLINE,
                                    size=48,
                                    color=Colors.ERROR
                                ),
                                alignment=ft.alignment.center,
                                visible=status == 'error'
                            ) if status == 'error' else ft.Container()
                        ]
                    ),
                    # File info section
                    ft.Container(
                        content=ft.Column(
                            [
                                # Filename
                                ft.Text(
                                    file_data['name'],
                                    size=13,
                                    color=Colors.TEXT_PRIMARY if status != 'error' else Colors.ERROR,
                                    weight=ft.FontWeight.W_500,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS
                                ),
                                # File size and format
                                ft.Text(
                                    f"{file_size_mb:.1f} MB • {file_ext}",
                                    size=11,
                                    color=Colors.TEXT_SECONDARY
                                ),
                                # Retry button only (Actions moved to context menu)
                                ft.Container(
                                    content=ft.TextButton(
                                        text="Retry",
                                        style=ft.ButtonStyle(
                                            color=Colors.ERROR,
                                            padding=ft.padding.symmetric(horizontal=0, vertical=4)
                                        ),
                                        visible=status == 'error',
                                        height=30
                                    ),
                                    alignment=ft.alignment.center_left
                                ) if status == 'error' else ft.Container(height=5)
                            ],
                            spacing=4
                        ),
                        padding=ft.padding.only(top=8, left=4, right=4, bottom=4)
                    )
                ]
                
                grid_items.append(
                    ft.GestureDetector(
                        content=ft.Container(
                            content=ft.Column(
                                card_content,
                                spacing=0,
                                horizontal_alignment=ft.CrossAxisAlignment.START
                            ),
                            padding=12,
                            bgcolor=Colors.BG_SECONDARY,
                            border=ft.border.all(1, Colors.BORDER),
                            border_radius=8,
                            clip_behavior=ft.ClipBehavior.HARD_EDGE
                        ),
                        on_secondary_tap_down=lambda e, f=file_data: show_context_menu(e, f)
                    )
                )
            
            # Add "Drop files here" card at the end
            grid_items.append(
                ft.GestureDetector(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Icon(
                                    ft.icons.ADD,
                                    size=48,
                                    color=Colors.TEXT_SECONDARY
                                ),
                                ft.Text(
                                    "Drop files here",
                                    size=13,
                                    color=Colors.TEXT_SECONDARY
                                )
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=8
                        ),
                        # width=204, # Remove fixed width
                        height=250,  # Match card height
                        border=ft.border.all(2, Colors.BORDER),
                        border_radius=8,
                        bgcolor=Colors.BG_PRIMARY
                    ),
                    on_tap=lambda _: file_picker.pick_files(
                        allow_multiple=True,
                        allowed_extensions=["png", "jpg", "jpeg", "webp", "bmp"]
                    )
                )
            )
            
            # Use GridView for better layout control
            file_list_container.content = ft.GridView(
                controls=grid_items,
                max_extent=230,  # Slightly larger to fit 180px image + padding
                child_aspect_ratio=0.7,
                spacing=16,
                run_spacing=16,
                padding=24,
                expand=True
            )
        
        page.update()
    
    # batch_toolbar removed - controls moved to top_nav
    
    # Progress tracking
    progress_text = ft.Text(
        "0/0 Ready",
        size=14,
        color=Colors.TEXT_SECONDARY
    )
    
    progress_indicator = ft.ProgressRing(
        value=0, 
        width=50, 
        height=50, 
        stroke_width=4, 
        color=Colors.ACCENT,
        bgcolor=Colors.BORDER
    )
    
    progress_label = ft.Text("0%", size=12, weight=ft.FontWeight.BOLD, color=Colors.TEXT_PRIMARY)

    progress_circle = ft.Stack(
        [
            progress_indicator,
            ft.Container(content=progress_label, alignment=ft.alignment.center, width=50, height=50)
        ],
        width=50,
        height=50
    )

    def update_progress_ui():
        done_count = len([f for f in files_to_process if f['status'] == 'done'])
        total = len(files_to_process)
        progress_text.value = f"{done_count}/{total} Ready"
        
        ratio = done_count / total if total > 0 else 0
        pct = int(ratio * 100)
        
        progress_label.value = f"{pct}%"
        progress_indicator.value = ratio
        progress_indicator.color = Colors.ACCENT
            
        progress_label.update()
        progress_indicator.update()
        progress_text.update()
    
    def process_images_thread():
        """Background processing thread"""
        global processed_results
        
        for idx, file_data in enumerate(files_to_process):
            if file_data['status'] != 'pending':
                continue
            
            try:
                # Update status
                file_data['status'] = 'processing'
                update_file_list()
                
                # Process image
                result_img = remover.remove_background(file_data['path'])
                
                # Save to temp
                temp_path = Path(TEMP_DIR) / f"no_bg_{file_data['name']}"
                result_img.save(str(temp_path))
                
                # Update thumbnail with processed image
                try:
                    thumb_img = result_img.copy()
                    thumb_img.thumbnail((300, 300), Image.Resampling.LANCZOS)
                    thumb_buffer = io.BytesIO()
                    thumb_img.save(thumb_buffer, format='PNG')
                    file_data['thumbnail'] = base64.b64encode(thumb_buffer.getvalue()).decode()
                except Exception as e:
                    print(f"Error updating thumbnail: {e}")

                file_data['result_path'] = str(temp_path)
                file_data['status'] = 'done'
                processed_results[file_data['path']] = str(temp_path)
                
            except Exception as e:
                print(f"Processing error: {e}")
                file_data['status'] = 'error'
            
            # Update progress
            update_progress_ui()
            update_file_list()
        
        show_alert("Processing complete!", "success")
        page.update()
    
    def start_processing(e):
        if not remover:
            show_alert("Model not ready", "warning")
            page.update()
            return
        
        # Reset pending files
        for f in files_to_process:
            if f['status'] == 'error':
                f['status'] = 'pending'
        
        threading.Thread(target=process_images_thread, daemon=True).start()
        
        show_alert("Processing started...", "info")
        page.update()
    
    # Export functionality
    def on_export_result(e: ft.FilePickerResultEvent):
        if e.path:
            export_dir = Path(e.path)
            count = 0
            for file_data in files_to_process:
                if file_data['status'] == 'done' and file_data['result_path']:
                    src = Path(file_data['result_path'])
                    dst = export_dir / src.name
                    shutil.copy(src, dst)
                    count += 1
            
            show_alert(f"Exported {count} files to {export_dir}", "success")
            page.update()
    
    export_picker = ft.FilePicker(on_result=on_export_result)
    page.overlay.append(export_picker)
    
    def export_files(e):
        done_files = [f for f in files_to_process if f['status'] == 'done']
        if not done_files:
            show_alert("No processed files to export", "warning")
            page.update()
            return
        
        export_picker.get_directory_path()
    
    # Save single file logic
    current_save_file = {"path": None}
    
    def on_save_result(e: ft.FilePickerResultEvent):
        if e.path and current_save_file["path"]:
            try:
                shutil.copy(current_save_file["path"], e.path)
                show_alert(f"Saved to {e.path}", "success")
            except Exception as ex:
                show_alert(f"Save failed: {str(ex)}", "error")
            page.update()
            
    save_file_picker = ft.FilePicker(on_result=on_save_result)
    page.overlay.append(save_file_picker)
    
    def save_single_file(file_data):
        if file_data.get('result_path') and file_data['status'] == 'done':
            current_save_file["path"] = file_data['result_path']
            save_file_picker.save_file(
                file_name=f"no_bg_{Path(file_data['name']).stem}.png",
                allowed_extensions=["png"]
            )
        else:
            show_alert("No processed file to save", "warning")
            page.update()

    def delete_single_file(file_data):
        if file_data in files_to_process:
            files_to_process.remove(file_data)
            update_file_list()
            # Update progress
            update_progress_ui()
            page.update()

    # Context Menu (Floating)
    context_menu = ft.Stack([], visible=False, expand=True)
    page.overlay.append(context_menu)

    def close_context_menu(e=None):
        context_menu.visible = False
        context_menu.update()

    def show_context_menu(e, file_data):
        # Helper to create menu item
        def create_menu_item(icon, text, on_click, color=None, disabled=False):
            return ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(icon, size=18, color=color or Colors.TEXT_PRIMARY),
                        ft.Text(text, size=14, color=color or Colors.TEXT_PRIMARY)
                    ],
                    spacing=12
                ),
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
                on_click=lambda _: [on_click(file_data), close_context_menu()] if not disabled else None,
                opacity=0.5 if disabled else 1.0,
                bgcolor=Colors.BG_SECONDARY, # Default bg
                ink=True,
                border_radius=4,
            )

        # Menu content
        menu_content = ft.Container(
            content=ft.Column(
                [
                    create_menu_item(
                        ft.icons.DOWNLOAD, 
                        "Save Image", 
                        save_single_file,
                        disabled=file_data['status'] != 'done'
                    ),
                    ft.Divider(height=1, thickness=1, color=Colors.BORDER),
                    create_menu_item(
                        ft.icons.DELETE_OUTLINE, 
                        "Remove File", 
                        delete_single_file, 
                        color=Colors.ERROR
                    ),
                ],
                spacing=0,
            ),
            bgcolor=Colors.BG_SECONDARY,
            border=ft.border.all(1, Colors.BORDER),
            border_radius=8,
            shadow=ft.BoxShadow(
                blur_radius=10,
                color=ft.colors.with_opacity(0.3, "black"),
                offset=ft.Offset(0, 4)
            ),
            width=180,
            padding=4
        )
        
        # Update overlay controls
        print(f"Show menu at {e.global_x}, {e.global_y}")
        context_menu.controls = [
            # Transparent backdrop to close menu on click outside
            ft.Container(
                content=ft.GestureDetector(
                    on_tap=close_context_menu,
                    on_secondary_tap=close_context_menu,
                    on_pan_start=lambda _: close_context_menu(), # Close on scroll/drag
                ),
                bgcolor=ft.colors.TRANSPARENT,
                width=page.width,
                height=page.height,
            ),
            # The menu positioned at cursor
            menu_content
        ]
        
        # Position menu
        menu_content.left = e.global_x
        menu_content.top = e.global_y
        context_menu.width = page.width
        context_menu.height = page.height
        context_menu.left = 0
        context_menu.top = 0
        context_menu.visible = True
        context_menu.update()

    bottom_bar = ft.Container(
        content=ft.Row(
            [
                ft.Row(
                    [
                        progress_circle,
                        progress_text
                    ],
                    spacing=12
                ),
                ft.Row(
                    [
                        ft.ElevatedButton(
                            content=ft.Row(
                                [
                                    ft.Icon(ft.icons.CONTENT_CUT, size=18),
                                    ft.Text("Start Cutout", size=14)
                                ],
                                spacing=8
                            ),
                            style=ft.ButtonStyle(
                                bgcolor=Colors.ACCENT,
                                color=Colors.TEXT_PRIMARY,
                                padding=ft.padding.symmetric(horizontal=24, vertical=16),
                                shape=ft.RoundedRectangleBorder(radius=8)
                            ),
                            on_click=start_processing
                        ),
                        ft.OutlinedButton(
                            content=ft.Row(
                                [
                                    ft.Icon(ft.icons.DOWNLOAD, size=18),
                                    ft.Text("Export", size=14)
                                ],
                                spacing=8
                            ),
                            style=ft.ButtonStyle(
                                color=Colors.TEXT_PRIMARY,
                                side=ft.BorderSide(1, Colors.BORDER),
                                padding=ft.padding.symmetric(horizontal=24, vertical=16),
                                shape=ft.RoundedRectangleBorder(radius=8)
                            ),
                            on_click=export_files
                        )
                    ],
                    spacing=12
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        ),
        padding=ft.padding.symmetric(horizontal=24, vertical=16),
        bgcolor=Colors.BG_SECONDARY,
        border=ft.border.only(top=ft.BorderSide(1, Colors.BORDER))
    )
    
    batch_view = ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=file_list_container,
                    padding=24,
                    expand=True
                ),
                bottom_bar
            ],
            spacing=0
        ),
        expand=True,
        visible=False
    )
    
    # --- Main Layout ---
    main_container = ft.Column(
        [
            top_nav,
            empty_view,
            batch_view
        ],
        spacing=0,
        expand=True,
        visible=False
    )
    
    page.add(
        ft.Column(
            [
                loading_screen,
                main_container
            ],
            spacing=0,
            expand=True
        )
    )
    
    # Start model loading
    threading.Thread(target=load_model_thread, daemon=True).start()

if __name__ == "__main__":
    # Calculate absolute assets path
    if getattr(sys, 'frozen', False):
        # In PyInstaller bundle
        # Try relative to executable (Contents/MacOS)
        assets_path = Path(sys.executable).parent / "assets"
        if not assets_path.exists():
             # Try sys._MEIPASS
             assets_path = Path(sys._MEIPASS) / "assets"
    else:
        # Dev mode
        assets_path = Path(__file__).parent / "assets"
        
    ft.app(target=main, assets_dir=str(assets_path))
