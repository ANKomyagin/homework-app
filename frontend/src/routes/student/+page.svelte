<script>
	import { onMount } from 'svelte';

	let lessons = $state([]);
	let userCreatedAt = $state('2026-09-01');
	let selectedLesson = $state(null);
	let files = $state([]);
	let comment = $state('');
	let isUploading = $state(false);
	let message = $state({ text: '', isError: false });
	let fileInput = $state(null);

	let currentYear = $state(2026);
	let currentMonth = $state(9); // 9 = Октябрь

	const monthNames = [
		'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
		'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
	];

	onMount(async () => {
		await loadLessons();
	});

	async function loadLessons() {
		try {
			const res = await fetch('/api/student/lessons');
			if (res.ok) {
				const data = await res.json();
				lessons = data.lessons;
				userCreatedAt = data.user_created_at;

				if (lessons.length > 0) {
					// Если уже был выбран урок, обновляем его данные
					if (selectedLesson) {
						selectedLesson = lessons.find(l => l.id === selectedLesson.id) || lessons[0];
					} else {
						selectedLesson = lessons.find(l => !l.submission) || lessons[0];
					}
					comment = selectedLesson?.submission?.comment || '';
				}
			} else {
				window.location.href = '/';
			}
		} catch (e) {
			console.error(e);
		}
	}

	function selectLesson(lesson) {
		selectedLesson = lesson;
		comment = lesson.submission?.comment || '';
		message = { text: '', isError: false };
		files = [];
	}

	// Сетка дней календаря
	let calendarDays = $derived.by(() => {
		const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
		const firstDayOfWeek = (new Date(currentYear, currentMonth, 1).getDay() + 6) % 7;

		const items = [];
		for (let i = 0; i < firstDayOfWeek; i++) {
			items.push({ type: 'empty' });
		}

		const todayStr = new Date().toISOString().split('T')[0];
		const userRegDateStr = userCreatedAt.split('T')[0];

		for (let d = 1; d <= daysInMonth; d++) {
			const dayOfWeek = (firstDayOfWeek + d - 1) % 7;
			const dateStr = `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
			const isLessonDay = (dayOfWeek === 1 || dayOfWeek === 3); // ВТ или ЧТ

			const lesson = lessons.find(l => l.date === dateStr);

			let status = 'none';
			if (isLessonDay && lesson) {
				if (lesson.submission) {
					status = lesson.submission.is_on_time ? 'on_time' : 'late';
				} else if (dateStr < todayStr) {
					// Красным подсвечиваем только если урок был ПОСЛЕ дня регистрации ученика!
					if (dateStr >= userRegDateStr) {
						status = 'missed';
					} else {
						status = 'before_reg'; // Не штрафуем за дни до регистрации
					}
				} else {
					status = 'upcoming';
				}
			}

			items.push({
				dayNumber: d,
				dateStr,
				isLessonDay,
				lesson,
				status
			});
		}
		return items;
	});

	function prevMonth() {
		if (currentMonth === 0) { currentMonth = 11; currentYear--; } else { currentMonth--; }
	}

	function nextMonth() {
		if (currentMonth === 11) { currentMonth = 0; currentYear++; } else { currentMonth++; }
	}

	async function submitHomework() {
		if (!selectedLesson) return;

		isUploading = true;
		message = { text: '', isError: false };

		const formData = new FormData();
		formData.append('text_comment', comment);
		files.forEach(f => formData.append('files', f));

		try {
			const res = await fetch(`/api/submissions/${selectedLesson.id}`, {
				method: 'POST',
				body: formData
			});
			if (res.ok) {
				message = { text: 'Изменения сохранены!', isError: false };
				files = [];
				await loadLessons();
			} else {
				const err = await res.json();
				message = { text: err.detail || 'Ошибка отправки', isError: true };
			}
		} catch (e) {
			message = { text: 'Ошибка сети', isError: true };
		} finally {
			isUploading = false;
		}
	}

	async function deleteAttachedFile(fileId) {
		if (!confirm('Удалить этот файл?')) return;
		try {
			const res = await fetch(`/api/submissions/files/${fileId}`, { method: 'DELETE' });
			if (res.ok) {
				await loadLessons();
			}
		} catch (e) {
			alert('Не удалось удалить файл');
		}
	}

	function formatDate(isoStr) {
		if (!isoStr) return '';
		const d = new Date(isoStr);
		return d.toLocaleDateString('ru-RU') + ' в ' + d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
	}
</script>

<svelte:head><title>Кабинет ученика</title></svelte:head>

<div class="min-h-screen bg-slate-50 p-4 md:p-8">
	<div class="max-w-4xl mx-auto space-y-6">

		<!-- Верхняя плашка -->
		<div class="flex justify-between items-center bg-white px-6 py-4 rounded-2xl shadow-xs border border-slate-100">
			<div>
				<h1 class="text-xl font-bold text-slate-800">Кабинет ученика</h1>
				<p class="text-xs text-slate-400">Английский язык • 10 А класс</p>
			</div>
			<button onclick={() => window.location.href = '/'} class="text-xs text-slate-400 hover:text-red-500 font-medium transition">
				Выйти
			</button>
		</div>

		<!-- Карточка календаря -->
		<div class="bg-white rounded-2xl p-6 md:p-8 shadow-xs border border-slate-100 space-y-6">
			
			<!-- Шапка календаря -->
			<div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-100 pb-5">
				<div class="flex items-center gap-3">
					<button onclick={prevMonth} class="w-9 h-9 rounded-xl border border-slate-200 flex items-center justify-center hover:bg-slate-50 text-slate-600 transition">
						←
					</button>
					<h2 class="text-lg font-bold text-slate-800 min-w-[150px] text-center">
						{monthNames[currentMonth]} {currentYear}
					</h2>
					<button onclick={nextMonth} class="w-9 h-9 rounded-xl border border-slate-200 flex items-center justify-center hover:bg-slate-50 text-slate-600 transition">
						→
					</button>
				</div>

				<!-- Обновленная легенда -->
				<div class="flex flex-wrap items-center gap-4 text-xs font-medium text-slate-600">
					<div class="flex items-center gap-1.5">
						<span class="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
						<span>Сдано (✓)</span>
					</div>
					<div class="flex items-center gap-1.5">
						<span class="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
						<span>С опозданием (~)</span>
					</div>
					<div class="flex items-center gap-1.5">
						<span class="w-2.5 h-2.5 rounded-full bg-rose-400"></span>
						<span>Пропуск (×)</span>
					</div>
					<div class="flex items-center gap-1.5">
						<span class="w-2.5 h-2.5 rounded-full bg-slate-200"></span>
						<span>Нет домашнего</span>
					</div>
				</div>
			</div>

			<!-- Дни недели -->
			<div class="grid grid-cols-7 gap-2 md:gap-3 text-center text-xs font-bold text-slate-400 uppercase">
				<div>ПН</div>
				<div class="text-blue-600 font-extrabold">ВТ *</div>
				<div>СР</div>
				<div class="text-blue-600 font-extrabold">ЧТ *</div>
				<div>ПТ</div>
				<div>СБ</div>
				<div>ВС</div>
			</div>

			<!-- Сетка дней -->
			<div class="grid grid-cols-7 gap-2 md:gap-3">
				{#each calendarDays as item}
					{#if item.type === 'empty'}
						<div class="aspect-square"></div>
					{:else}
						<!-- svelte-ignore a11y_click_events_have_key_events -->
						<!-- svelte-ignore a11y_no_static_element_interactions -->
						<div
							onclick={() => { if (item.isLessonDay && item.lesson) selectLesson(item.lesson); }}
							class={`aspect-square rounded-2xl flex flex-col items-center justify-center relative transition-all select-none
								${item.isLessonDay ? 'cursor-pointer hover:scale-105 shadow-xs' : 'bg-slate-50/40 text-slate-300 border border-slate-100'}
								${selectedLesson?.id === item.lesson?.id && item.isLessonDay ? 'ring-3 ring-blue-500' : ''}
								${item.status === 'on_time' ? 'bg-emerald-50 border-2 border-emerald-400 text-emerald-800' : ''}
								${item.status === 'late' ? 'bg-amber-50 border-2 border-amber-300 text-amber-800' : ''}
								${item.status === 'missed' ? 'bg-rose-50 border-2 border-rose-300 text-rose-800' : ''}
								${item.status === 'before_reg' ? 'bg-slate-50 border border-slate-200 text-slate-400' : ''}
								${item.status === 'upcoming' ? 'bg-blue-50 border-2 border-blue-200 text-blue-800 hover:border-blue-400' : ''}
							`}
						>
							<span class="text-sm font-bold">{item.dayNumber}</span>
							
							{#if item.status === 'on_time'}
								<span class="text-xs font-black text-emerald-600">✓</span>
							{:else if item.status === 'late'}
								<span class="text-xs font-black text-amber-500">~</span>
							{:else if item.status === 'missed'}
								<span class="text-xs font-black text-rose-500">×</span>
							{:else if item.status === 'upcoming'}
								<span class="text-[10px] font-semibold text-blue-500 uppercase">Сдать</span>
							{/if}
						</div>
					{/if}
				{/each}
			</div>
		</div>

		<!-- Зона просмотра и редактирования выбранного урока -->
		{#if selectedLesson}
			<div class="bg-white rounded-2xl p-6 md:p-8 shadow-xs border border-slate-100 space-y-6">
				<div class="flex flex-col sm:flex-row justify-between items-start sm:items-center border-b border-slate-100 pb-4 gap-2">
					<div>
						<span class="text-xs font-bold text-blue-600 uppercase tracking-wide">Урок английского</span>
						<h3 class="text-xl font-bold text-slate-800">
							{new Date(selectedLesson.date).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })}
						</h3>
					</div>

					{#if selectedLesson.submission}
						<div class="text-right">
							<span class="px-3 py-1 rounded-full text-xs font-bold inline-block {selectedLesson.submission.is_on_time ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}">
								{selectedLesson.submission.is_on_time ? '✓ Сдано вовремя' : '~ Сдано с опозданием'}
							</span>
							<div class="text-[11px] text-slate-400 mt-1">
								Сдано: {formatDate(selectedLesson.submission.submitted_at)}
								{#if selectedLesson.submission.updated_at && selectedLesson.submission.updated_at !== selectedLesson.submission.submitted_at}
									<br><span class="text-amber-600 font-medium">Изменено: {formatDate(selectedLesson.submission.updated_at)}</span>
								{/if}
							</div>
						</div>
					{/if}
				</div>

				<!-- Отзыв учителя -->
				{#if selectedLesson.submission?.teacher_feedback}
					<div class="bg-amber-50 border border-amber-200 p-4 rounded-xl space-y-1">
						<div class="text-xs font-bold text-amber-800">Комментарий преподавателя:</div>
						<div class="text-sm text-amber-900">{selectedLesson.submission.teacher_feedback}</div>
					</div>
				{/if}

				<!-- Список уже загруженных файлов -->
				{#if selectedLesson.submission?.files?.length > 0}
					<div>
						<label class="block text-xs font-bold text-slate-500 uppercase tracking-wide mb-2">Прикрепленные файлы</label>
						<ul class="space-y-2">
							{#each selectedLesson.submission.files as f}
								<li class="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-200 text-sm">
									<a href={f.url} target="_blank" class="text-blue-600 hover:underline truncate max-w-[80%] font-medium">
										📎 {f.name}
									</a>
									<button onclick={() => deleteAttachedFile(f.id)} class="text-xs text-rose-500 hover:text-rose-700 font-semibold px-2 py-1 hover:bg-rose-50 rounded">
										Удалить
									</button>
								</li>
							{/each}
						</ul>
					</div>
				{/if}

				<!-- Добавление новых файлов -->
				<div class="space-y-4">
					<label class="block text-xs font-bold text-slate-500 uppercase tracking-wide" for="file-upload-input">
						{selectedLesson.submission ? 'Прикрепить еще файлы' : 'Прикрепить файлы'}
					</label>
					
					<!-- svelte-ignore a11y_click_events_have_key_events -->
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<div 
						onclick={() => fileInput?.click()}
						class="border-2 border-dashed border-slate-200 hover:border-blue-400 bg-slate-50 rounded-xl p-5 text-center cursor-pointer transition"
					>
						<p class="text-sm text-slate-500">Нажмите, чтобы выбрать файлы (фото, PDF, Word)</p>
						<input id="file-upload-input" type="file" multiple class="hidden" bind:this={fileInput} onchange={(e) => {
							if (e.target.files) files = [...files, ...Array.from(e.target.files)];
						}}>
					</div>

					{#if files.length > 0}
						<div class="text-xs text-slate-500 font-medium">Новые файлы к отправке:</div>
						<ul class="space-y-1">
							{#each files as f, i}
								<li class="flex justify-between items-center bg-blue-50/50 p-2.5 rounded-lg border border-blue-100 text-xs">
									<span class="truncate max-w-[80%]">{f.name}</span>
									<button onclick={() => files = files.filter((_, idx) => idx !== i)} class="text-rose-500 font-bold px-1">✕</button>
								</li>
							{/each}
						</ul>
					{/if}

					<div>
						<label class="block text-xs font-bold text-slate-500 uppercase tracking-wide mb-1" for="comment-area">Комментарий к работе</label>
						<textarea 
							id="comment-area"
							bind:value={comment} 
							rows="2" 
							placeholder="Ваш комментарий..."
							class="w-full rounded-xl border border-slate-200 p-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
						></textarea>
					</div>

					{#if message.text}
						<div class={`p-3 rounded-xl text-sm ${message.isError ? 'bg-rose-50 text-rose-700' : 'bg-emerald-50 text-emerald-700'}`}>
							{message.text}
						</div>
					{/if}

					<button 
						onclick={submitHomework}
						disabled={isUploading}
						class="w-full py-3 bg-blue-600 text-white rounded-xl font-bold hover:bg-blue-700 transition disabled:opacity-50"
					>
						{isUploading ? 'Сохранение...' : (selectedLesson.submission ? 'Сохранить изменения' : 'Отправить ДЗ')}
					</button>
				</div>
			</div>
		{/if}

	</div>
</div>
