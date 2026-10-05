<script>
	import { onMount } from 'svelte';

	let classes = $state([]);
	let selectedClassId = $state(null);
	let dashboardData = $state({ lessons: [], students: [], submissions: {} });
	let isLoading = $state(true);

	// Состояние открытого модального окна проверки
	let activeSubmission = $state(null);
	let feedbackText = $state('');
	// Состояние холстов
	let canvases = {};
	let isDrawing = {};
	let isModified = {};

	// Переменные для Шаг Назад / Вперед
	let canvasStates = $state({});
	let lastActiveFileId = $state(null);

	onMount(async () => {
		try {
			const res = await fetch('/api/classes');
			if (res.ok) {
				classes = await res.json();
				if (classes.length > 0) {
					selectedClassId = classes[0].id;
					await loadDashboard();
				}
			} else {
				window.location.href = '/';
			}
		} catch (e) {
			console.error(e);
		}
	});

	async function loadDashboard() {
		if (!selectedClassId) return;
		isLoading = true;
		try {
			const res = await fetch(`/api/teacher/dashboard/${selectedClassId}`);
			if (res.ok) {
				dashboardData = await res.json();
			}
		} catch (e) {
			console.error(e);
		} finally {
			isLoading = false;
		}
	}

	function openSubmission(sub, studentName, lessonTitle) {
		activeSubmission = { ...sub, studentName, lessonTitle };
		feedbackText = sub.feedback || '';
		canvases = {};
		isDrawing = {};
		isModified = {};
		canvasStates = {}; // Сбрасываем историю
		lastActiveFileId = null;
	}

	function closeSubmission() {
		activeSubmission = null;
	}

	function initCanvas(imgElement, fileId) {
		const canvas = canvases[fileId];
		if (!canvas || !imgElement) return;
		canvas.width = imgElement.naturalWidth || imgElement.width;
		canvas.height = imgElement.naturalHeight || imgElement.height;
		const ctx = canvas.getContext('2d');
		ctx.strokeStyle = '#ef4444'; 
		ctx.lineWidth = 4;
		ctx.lineCap = 'round';
		ctx.lineJoin = 'round';

		// Сохраняем пустое состояние для старта Ctrl+Z
		if (!canvasStates[fileId]) {
			canvasStates[fileId] = { history: [canvas.toDataURL()], step: 0 };
		}
	}

	function startDraw(e, fileId) {
		isDrawing[fileId] = true;
		isModified[fileId] = true;
		lastActiveFileId = fileId; // Запоминаем, где рисуем для Ctrl+Z
		draw(e, fileId);
	}

	function stopDraw(fileId) {
		if (!isDrawing[fileId]) return;
		isDrawing[fileId] = false;
		const ctx = canvases[fileId]?.getContext('2d');
		ctx?.beginPath();

		// Сохраняем шаг в историю
		const canvas = canvases[fileId];
		const state = canvasStates[fileId];
		state.history = state.history.slice(0, state.step + 1);
		state.history.push(canvas.toDataURL());
		state.step++;
		canvasStates[fileId] = { ...state }; // Триггер реактивности
	}

	function draw(e, fileId) {
		if (!isDrawing[fileId] || !canvases[fileId]) return;
		const canvas = canvases[fileId];
		const ctx = canvas.getContext('2d');
		const rect = canvas.getBoundingClientRect();
		const scaleX = canvas.width / rect.width;
		const scaleY = canvas.height / rect.height;

		const clientX = e.touches ? e.touches[0].clientX : e.clientX;
		const clientY = e.touches ? e.touches[0].clientY : e.clientY;

		const x = (clientX - rect.left) * scaleX;
		const y = (clientY - rect.top) * scaleY;

		ctx.lineTo(x, y);
		ctx.stroke();
		ctx.beginPath();
		ctx.moveTo(x, y);
	}

	// ФУНКЦИИ ОТМЕНЫ
	function undo(fileId) {
		const state = canvasStates[fileId];
		if (!state || state.step <= 0) return;
		state.step--;
		restoreState(fileId, state.history[state.step]);
		canvasStates[fileId] = { ...state };
		isModified[fileId] = state.step > 0;
	}

	function redo(fileId) {
		const state = canvasStates[fileId];
		if (!state || state.step >= state.history.length - 1) return;
		state.step++;
		restoreState(fileId, state.history[state.step]);
		canvasStates[fileId] = { ...state };
		isModified[fileId] = state.step > 0;
	}

	function restoreState(fileId, dataUrl) {
		const canvas = canvases[fileId];
		const ctx = canvas.getContext('2d');
		const img = new Image();
		img.src = dataUrl;
		img.onload = () => {
			ctx.clearRect(0, 0, canvas.width, canvas.height);
			ctx.drawImage(img, 0, 0);
		};
	}

	// Глобальный перехватчик Ctrl+Z / Ctrl+Y
	function handleKeydown(e) {
		if (!activeSubmission) return;
		if (e.ctrlKey || e.metaKey) {
			const targetFileId = lastActiveFileId || activeSubmission.files.find(f => f.type.includes('image'))?.id;
			if (!targetFileId) return;

			if (e.key.toLowerCase() === 'z') {
				e.preventDefault();
				if (e.shiftKey) redo(targetFileId);
				else undo(targetFileId);
			}
			if (e.key.toLowerCase() === 'y') {
				e.preventDefault();
				redo(targetFileId);
			}
		}
	}

	async function saveFeedback() {
		if (!activeSubmission) return;
		
		// 1. Отправляем текстовый отзыв
		await fetch(`/api/teacher/feedback/${activeSubmission.id}`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ feedback: feedbackText })
		});

		// 2. Отправляем разрисованные картинки
		for (const file of activeSubmission.files) {
			// Если файл — картинка, и учитель на ней что-то нарисовал
			if (file.type.includes('image') && isModified[file.id]) {
				const img = document.getElementById(`img-${file.id}`);
				const canvas = canvases[file.id];
				
				// Создаем временный холст для склейки оригинала с красным маркером
				const tempCanvas = document.createElement('canvas');
				tempCanvas.width = canvas.width;
				tempCanvas.height = canvas.height;
				const tCtx = tempCanvas.getContext('2d');
				
				// Склеиваем слои
				tCtx.drawImage(img, 0, 0, tempCanvas.width, tempCanvas.height);
				tCtx.drawImage(canvas, 0, 0);
				
				// Получаем итоговую картинку и шлем на сервер
				const dataUrl = tempCanvas.toDataURL('image/webp', 0.9);
				
				await fetch(`/api/teacher/check_file/${file.id}`, {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ image_data: dataUrl })
				});
			}
		}

		alert('Отзыв сохранен!');
		await loadDashboard();
		closeSubmission();
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="min-h-screen bg-gray-50 p-6 md:p-10">
	<div class="max-w-6xl mx-auto bg-white rounded-2xl shadow-sm p-6">
		<div class="flex justify-between items-center mb-6">
			<h1 class="text-2xl font-bold text-gray-900">Панель учителя</h1>
			<div class="flex items-center gap-4">
				<label class="sr-only" for="teacher-class-select">Класс</label>
				<select id="teacher-class-select" bind:value={selectedClassId} onchange={loadDashboard} class="rounded-lg border border-gray-300 py-2 px-3 bg-white">
					{#each classes as sc}
						<option value={sc.id}>Класс {sc.name}</option>
					{/each}
				</select>
				<button class="text-red-500 hover:text-red-700 font-medium" onclick={() => window.location.href = '/'}>Выйти</button>
			</div>
		</div>

		{#if isLoading}
			<p class="text-gray-500">Загрузка данных...</p>
		{:else}
			<div class="overflow-x-auto">
				<table class="w-full text-sm text-left text-gray-500 border border-gray-200">
					<thead class="text-xs text-gray-700 uppercase bg-gray-100">
						<tr>
							<th class="px-6 py-4 border-b border-gray-300 border-r-2 font-bold min-w-[220px] sticky left-0 bg-gray-100 z-20">ФИО Ученика</th>
							{#each dashboardData.lessons as lesson}
								<th class="px-6 py-4 border-b text-center border-r min-w-[150px]">
									<div>{new Date(lesson.date).toLocaleDateString('ru-RU')}</div>
									<div class="font-normal text-gray-500">{lesson.title}</div>
								</th>
							{/each}
						</tr>
					</thead>
					<tbody>
						{#each dashboardData.students as student, index}
							<!-- Добавили класс group для синхронизации hover-эффекта -->
							<tr class="bg-white border-b hover:bg-gray-50 group">
								
								<!-- Сделали ячейку липкой и добавили цвет фона -->
								<td class="px-6 py-4 font-medium text-gray-900 border-gray-200 border-r-2 sticky left-0 bg-white group-hover:bg-gray-50 z-10 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.05)]">
									{index + 1}. {student.name}
								</td>
								{#each dashboardData.lessons as lesson}
									{@const sub = dashboardData.submissions[`${student.id}_${lesson.id}`]}
									<td class="px-6 py-4 text-center border-r">
										{#if sub}
											{@const isChecked = sub.feedback || (sub.files && sub.files.some(f => f.checked_url))}
											<div class="flex flex-col items-center gap-1.5">
												<button 
													onclick={() => openSubmission(sub, student.name, lesson.title)}
													class={`inline-flex items-center justify-center px-3 py-1 text-xs font-medium rounded-full cursor-pointer hover:shadow transition
													${sub.is_on_time ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}
												>
													{sub.is_on_time ? 'Вовремя' : 'С опозданием'}
												</button>
												
												{#if isChecked}
													<span class="text-[10px] font-bold text-emerald-600 bg-emerald-50 border border-emerald-100 px-2 py-0.5 rounded-md">
														✅ Проверено
													</span>
												{/if}
											</div>
										{:else}
											<span class="text-gray-300">-</span>
										{/if}
									</td>
								{/each}
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	</div>
</div>

<!-- Модальное окно просмотра и рисования поверх задания -->
{#if activeSubmission}
	<div class="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 z-50">
		<div class="bg-white rounded-2xl max-w-4xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
			<!-- Шапка модалки -->
			<div class="flex justify-between items-center p-4 border-b border-gray-100">
				<div>
					<h3 class="font-bold text-gray-900 text-lg">{activeSubmission.studentName}</h3>
					<p class="text-xs text-gray-500">{activeSubmission.lessonTitle}</p>
				</div>
				<button class="text-gray-400 hover:text-gray-600 text-2xl font-bold" onclick={closeSubmission}>✕</button>
			</div>

			<!-- Контент: Просмотр файлов -->
			<div class="p-6 overflow-y-auto space-y-6 flex-1">
				{#if activeSubmission.comment}
					<div class="bg-blue-50 p-3 rounded-lg text-sm text-blue-900">
						<strong>Комментарий ученика:</strong> {activeSubmission.comment}
					</div>
				{/if}

				<div>
					<h4 class="font-semibold text-gray-800 mb-3">Прикрепленные файлы:</h4>
					{#if activeSubmission.files.length === 0}
						<p class="text-gray-400 text-sm">Файлов нет</p>
					{:else}
						<div class="space-y-6">
							{#each activeSubmission.files as file}
								<div class="border rounded-xl p-4 bg-gray-50 space-y-3">
									<div class="flex justify-between items-center">
										<span class="font-medium text-sm text-gray-700">{file.name}</span>
										<a href={file.url} target="_blank" download class="text-xs text-blue-600 hover:underline">Скачать оригинал</a>
									</div>

									<!-- Если картинка: показываем холст для рисования -->
									{#if file.type.includes('image')}
										<div class="flex justify-between items-end">
											<p class="text-xs text-gray-500">Рисуйте пальцем или мышкой. Доступны Ctrl+Z и Ctrl+Y</p>
											
											<!-- Кнопки Отмены и Возврата (для мобилок) -->
											<div class="flex gap-2">
												<button 
													disabled={!canvasStates[file.id] || canvasStates[file.id].step <= 0}
													onclick={() => undo(file.id)}
													class="px-2.5 py-1 text-xs font-medium bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 disabled:opacity-40 transition shadow-xs flex items-center gap-1"
												>↩ Отменить</button>
												<button 
													disabled={!canvasStates[file.id] || canvasStates[file.id].step >= canvasStates[file.id].history.length - 1}
													onclick={() => redo(file.id)}
													class="px-2.5 py-1 text-xs font-medium bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 disabled:opacity-40 transition shadow-xs flex items-center gap-1"
												>↪ Вернуть</button>
											</div>
										</div>

										<div class="relative inline-block max-w-full overflow-hidden rounded-lg border bg-gray-200">
											<img 
												id="img-{file.id}"
												src={file.checked_url || file.url} 
												alt={file.name} 
												class="max-h-[700px] w-auto block select-none"
												onload={(e) => initCanvas(e.currentTarget, file.id)}
											/>
											<canvas 
												bind:this={canvases[file.id]}
												onmousedown={(e) => startDraw(e, file.id)}
												onmouseup={() => stopDraw(file.id)}
												onmousemove={(e) => draw(e, file.id)}
												onmouseout={() => stopDraw(file.id)}
												ontouchstart={(e) => startDraw(e, file.id)}
												ontouchend={() => stopDraw(file.id)}
												ontouchmove={(e) => draw(e, file.id)}
												class="absolute inset-0 cursor-crosshair touch-none w-full h-full"
											></canvas>
										</div>
									{:else if file.type.includes('pdf')}
										<!-- Если PDF: встраиваем встроенный фрейм предпросмотра -->
										<iframe src={file.url} title="PDF viewer" class="w-full h-96 rounded border"></iframe>
									{:else}
										<!-- Word и другие форматы -->
										<div class="p-4 bg-white rounded border flex items-center gap-3">
											<span class="text-2xl">📄</span>
											<div>
												<p class="text-sm font-medium text-gray-700">{file.name}</p>
												<p class="text-xs text-gray-400">Предпросмотр недоступен для этого формата</p>
											</div>
										</div>
									{/if}
								</div>
							{/each}
						</div>
					{/if}
				</div>

				<!-- Отзыв учителя -->
				<div>
					<label class="block text-sm font-semibold text-gray-800 mb-2" for="teacher-feedback-text">Обратная связь ученику</label>
					<textarea 
						id="teacher-feedback-text"
						bind:value={feedbackText} 
						rows="3" 
						class="w-full rounded-lg border border-gray-300 p-3 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 resize-none"
						placeholder="Напишите замечания или оценку..."
					></textarea>
				</div>
			</div>

			<!-- Подвал модалки -->
			<div class="p-4 border-t border-gray-100 flex justify-end gap-3 bg-gray-50">
				<button class="px-4 py-2 border rounded-lg text-sm text-gray-600 hover:bg-gray-100" onclick={closeSubmission}>Закрыть</button>
				<button class="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700" onclick={saveFeedback}>Сохранить отзыв</button>
			</div>
		</div>
	</div>
{/if}
