// 监听搜索输入框的回车事件
document.getElementById('searchInput').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        searchIngredient();
    }
});

// 搜索功能
function searchIngredient() {
    const searchInput = document.getElementById('searchInput');
    const searchTerm = searchInput.value.trim();
    const resultsContainer = document.getElementById('searchResults');
    
    if (!searchTerm) {
        resultsContainer.innerHTML = '<p class="no-results">请输入要搜索的成分名称</p>';
        return;
    }

    // 显示加载状态
    resultsContainer.innerHTML = '<p class="loading">正在搜索...</p>';

    // 创建FormData对象
    const formData = new FormData();
    formData.append('query', searchTerm);

    // 调用搜索API
    fetch('/search', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            resultsContainer.innerHTML = `<p class="error">${data.error}</p>`;
            return;
        }
        displayResults(data);
    })
    .catch(error => {
        console.error('搜索出错:', error);
        resultsContainer.innerHTML = '<p class="error">搜索时发生错误，请稍后重试</p>';
    });
}

// 显示搜索结果
function displayResults(data) {
    const resultsContainer = document.getElementById('searchResults');
    
    if (!data || data.length === 0) {
        resultsContainer.innerHTML = '<p class="no-results">未找到相关成分</p>';
        return;
    }

    let html = '<div class="results-list">';
    data.forEach(item => {
        html += `
            <div class="result-item">
                <h3>${item.food_name}</h3>
                <p><strong>匹配成分：</strong>${item.match_content}</p>
                ${item.path ? `
                <button class="download-btn" onclick="downloadFile('${item.path}')">
                    <i class="bi bi-download"></i> 下载文件
                </button>` : ''}
            </div>
        `;
    });
    html += '</div>';

    resultsContainer.innerHTML = html;
}

// 下载文件
function downloadFile(filePath) {
    const formData = new FormData();
    formData.append('file_path', filePath);

    fetch('/ingredient/download', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (response.ok) {
            return response.blob();
        }
        throw new Error('文件下载失败');
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filePath.split('/').pop();
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
    })
    .catch(error => {
        console.error('下载出错:', error);
        showToast('文件下载失败，请稍后重试', 'error');
    });
} 