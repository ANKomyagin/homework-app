<script>
	import { onMount } from 'svelte';

	let classes = $state([]);
	let selectedClassId = $state(null);
	let dashboardData = $state({ lessons: [], students: [], submissions: {} });
	let isLoading = $state(true);

	// Состояние открытого модального окна проверки
	let activeSubmission = $state(null);
	let feedbackText = $state('');
	let canvasElement = $state(null);
	let isDrawing = $state(false);

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
	}

	function closeSubmission() {
		activeSubmission = null;
	}

	// Инициализация холста для рисования поверх картинки
	function initCanvas(imgElement) {
		if (!canvasElement || !imgElement) return;
		canvasElement.width = imgElement.naturalWidth || imgElement.width;
		canvasElement.height = imgElement.naturalHeight || imgElement.height;
		const ctx = canvasElement.getContext('2d');
		ctx.strokeStyle = '#ef4444'; // Красный маркер
		ctx.lineWidth = 4;
		ctx.lineCap = 'round';
	}

	function startDraw(e) {
		isDrawing = true;
		draw(e);
	}

	function stopDraw() {
		isDrawing = false;
		const ctx = canvasElement?.getContext('2d');
		ctx?.beginPath();
	}

	function draw(e) {
		if (!isDrawing || !canvasElement) return;
		const ctx = canvasElement.getContext('2d');
		const rect = canvasElement.getBoundingClientRect();
		const scaleX = canvasElement.width / rect.width;
		const scaleY = canvasElement.height / rect.height;

		const clientX = e.touches ? e.touches[0].clientX : e.clientX;
		const clientY = e.touches ? e.touches[0].clientY : e.clientY;

		const x = (clientX - rect.left) * scaleX;
		const y = (clientY - rect.top) * scaleY;

		ctx.lineTo(x, y);
		ctx.stroke();
		ctx.beginPath();
		ctx.moveTo(x, y);
	}

	async function saveFeedback() {
		if (!activeSubmission) return;
		await fetch(`/api/teacher/feedback/${activeSubmission.id}`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ feedback: feedbackText })
		});
		alert('Отзыв сохранен!');
		await loadDashboard();
		closeSubmission();
	}
</script>

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
							<th class="px-6 py-4 border-b border-r font-bold w-1/4">ФИО Ученика</th>
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
							<tr class="bg-white border-b hover:bg-gray-50">
								<td class="px-6 py-4 font-medium text-gray-900 border-r">
									{index + 1}. {student.name}
								</td>
								{#each dashboardData.lessons as lesson}
									{@const sub = dashboardData.submissions[`${student.id}_${lesson.id}`]}
									<td class="px-6 py-4 text-center border-r">
										{#if sub}
											<button 
												onclick={() => openSubmission(sub, student.name, lesson.title)}
												class={`inline-flex items-center justify-center px-3 py-1 text-xs font-medium rounded-full cursor-pointer hover:shadow transition
												${sub.is_on_time ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}
											>
												{sub.is_on_time ? 'Вовремя' : 'С опозданием'}
											</button>
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
										<p class="text-xs text-gray-500">Рисуйте пальцем или мышкой прямо по изображению:</p>
										<div class="relative inline-block max-w-full overflow-hidden rounded-lg border">
											<img 
												src={file.url} 
												alt={file.name} 
												class="max-h-[500px] w-auto block select-none"
												onload={(e) => initCanvas(e.currentTarget)}
											/>
											<canvas 
												bind:this={canvasElement}
												onmousedown={startDraw}
												onmouseup={stopDraw}
												onmousemove={draw}
												ontouchstart={startDraw}
												ontouchend={stopDraw}
												ontouchmove={draw}
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
