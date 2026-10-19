# Hệ thống đề xuất phim cá nhân hóa bằng KNNBaseline

**Môn học:** Hệ thống thông minh (Intelligent Systems)  
**Thuật toán chính:** User-based KNNBaseline, học độ lệch bằng ALS, kết hợp Pearson-baseline và shrinkage  
**Dữ liệu:** MovieLens 100K  
**Thời gian dự kiến:** 7–8 tuần  
**Trạng thái:** Tài liệu thiết kế trước triển khai; chưa có ứng dụng, lệnh chạy đã kiểm thử hoặc kết quả thực nghiệm.

## 1. Giới thiệu

Dự án xây dựng ứng dụng nhận điểm đánh giá phim của người dùng và trả về danh sách phim phù hợp. KNN tìm những người có cách đánh giá tương đồng; mô hình học thêm xu hướng chấm điểm của người dùng và xu hướng điểm của phim để điều chỉnh dự đoán.

Xem tài liệu đầy đủ: [Mô tả dự án](Mo_ta_du_an_KNN_De_xuat_phim.md).

## 2. Đầu vào và đầu ra

| Giai đoạn | Đầu vào | Đầu ra |
|---|---|---|
| Huấn luyện | Các bộ `user_id, movie_id, rating` trong train | Độ lệch người dùng/phim, ma trận tương đồng, cấu hình và artifact mô hình |
| Sử dụng | Hồ sơ và các điểm người dùng đã chấm | Top 10 phim chưa đánh giá, điểm dự đoán, nguồn và giải thích đề xuất |

Ví dụ: người dùng chấm Toy Story 5 sao, Star Wars 5 sao và Fargo 2 sao. Hệ thống tìm các hồ sơ tương đồng và xếp hạng các phim khác. Đây chỉ là ví dụ đầu vào; kết quả cụ thể phải được tính từ mô hình thật. Người dùng cuối không phải tải dataset.

## 3. Mục tiêu và phạm vi

- Xây dựng MVP có giao diện tìm phim, chấm điểm, xem lịch sử và nhận đề xuất.
- Có bước học tham số thật, kết hợp với dự đoán từ láng giềng.
- So sánh phim phổ biến, mô hình chỉ có bias, KNNBasic và KNNBaseline.
- Dùng dữ liệu thực; đánh giá tái lập và tránh rò rỉ dữ liệu.
- Có vai trò Người dùng, Quản trị viên và Data Scientist.

MVP không phát phim, thanh toán hoặc phục vụ quy mô thương mại. Poster và trailer là mở rộng tùy chọn.

## 4. KNNBaseline học gì?

Mô hình điểm nền gồm:

```text
Điểm nền = trung bình toàn train + độ lệch người dùng + độ lệch phim
```

Hai độ lệch được học bằng **ALS (Alternating Least Squares)** với regularization. Sau đó KNN tổng hợp phần đánh giá vượt lên hoặc thấp hơn điểm nền của các láng giềng. **SGD** là phương án học thay thế để thử nghiệm khi còn thời gian.

| Thành phần | Cách xác định |
|---|---|
| Độ lệch người dùng và phim | Học từ train bằng tối ưu sai số |
| Số láng giềng K, regularization, shrinkage | Chọn trên validation |
| Láng giềng và điểm đề xuất | Tính từ artifact và hồ sơ hợp lệ khi dự đoán |

Không gọi việc chọn K là học trọng số. Thuật toán này cũng không học embedding người dùng/phim như matrix factorization.

## 5. Dataset

**MovieLens 100K:** 100.000 lượt đánh giá của 943 người trên 1.682 phim; điểm từ 1 đến 5.

- [Trang chính thức](https://grouplens.org/datasets/movielens/100k/)
- [Tải ZIP](https://files.grouplens.org/datasets/movielens/ml-100k.zip)
- [README và điều kiện sử dụng](https://files.grouplens.org/datasets/movielens/ml-100k-README.txt)
- [Bản sao trên Hugging Face](https://huggingface.co/datasets/includeno/movielens-100k/tree/main)

Dùng `u.data` cho đánh giá và `u.item` cho thông tin phim. Ưu tiên nguồn GroupLens; không tự phân phối lại dữ liệu gốc trong repo. Dữ liệu cũ nên cần ghi giới hạn về danh mục phim và tính đại diện.

## 6. Quy trình triển khai dự kiến

1. Tải và kiểm tra dữ liệu; lưu nguồn, checksum và thống kê.
2. Làm sạch cấu trúc, kiểm tra rating và liên kết mã phim.
3. Chia tương tác theo người dùng: khoảng 70% train, 15% validation, 15% test; cố định seed.
4. Học bias và xây tương đồng chỉ từ train.
5. Thử cấu hình trên validation, chốt rồi đánh giá test.
6. Tích hợp giao diện và lưu đánh giá bằng SQLite.
7. Kiểm thử, hoàn thiện báo cáo PDF và demo.

Không điền rating thiếu thành điểm 0. Không dùng điểm validation/test để tính bias hoặc hồ sơ train.

## 7. Công nghệ và cấu trúc dự kiến

Python, pandas/NumPy, Streamlit, SQLite; có thể dùng Surprise làm bản tham chiếu cho KNNBaseline. Phiên bản thư viện sẽ được cố định khi triển khai.

| Đường dẫn dự kiến | Trách nhiệm |
|---|---|
| `app.py` | Giao diện |
| `src/data/` | Đọc, kiểm tra và chia dữ liệu |
| `src/models/` | Học bias, similarity và KNN |
| `src/services/` | Đề xuất, fallback và quản lý hồ sơ |
| `scripts/` | Các bước chuẩn bị, huấn luyện, đánh giá |
| `configs/` | Cấu hình dữ liệu và mô hình |
| `artifacts/` | Mô hình, split và metrics |
| `tests/` | Kiểm tra thuật toán và tích hợp |
| `docs/` | Báo cáo và sơ đồ |

**Hướng dẫn chạy:** sẽ được bổ sung sau khi có mã nguồn. Hiện tại các đường dẫn trên là thiết kế, chưa phải cấu trúc ứng dụng đã được tạo. Khi triển khai, README phải bổ sung môi trường, lệnh cài đặt, chuẩn bị dữ liệu, huấn luyện, đánh giá và khởi động đã kiểm chứng.

## 8. Đánh giá

| Mục tiêu | Chỉ số |
|---|---|
| Điểm dự đoán gần điểm thật | MAE, RMSE |
| Danh sách phim hữu ích | Precision@10, Recall@10, NDCG@10 |
| Mức phục vụ | Coverage và tỷ lệ fallback |
| Hoạt động ứng dụng | Độ trễ, dữ liệu lưu đúng, kiểm tra đầu vào |

Định nghĩa phim liên quan là phim người dùng chấm từ 4 sao trong tập được giữ lại. Mọi mô hình dùng chung split và tập ứng viên. Không đặt trước mức “accuracy 90%”; chưa có kết quả nào được đo.

## 9. Kế hoạch và bàn giao

| Tuần | Kết quả chính |
|---|---|
| 1 | Phạm vi, yêu cầu và kiểm tra dataset |
| 2 | Use case, kiến trúc và luồng dữ liệu |
| 3 | Preprocessing, splitting và mô hình đối chứng |
| 4 | Học bias, KNNBaseline và validation |
| 5 | MVP tích hợp |
| 6 | Test cuối, phân tích lỗi và kiểm thử |
| 7 | Báo cáo, README và hoàn thiện |
| 8 | Slide, diễn tập và đóng gói |

Nếu có 7 tuần, gộp hai tuần cuối. Bộ nộp gồm source code, README chạy được, hướng dẫn dữ liệu, báo cáo PDF, slide/demo, bảng đóng góp và khai báo sử dụng Generative AI.

## 10. Tài liệu tham khảo

- Rubric được cung cấp: `HK261_IS_Assignment_Rubric.pdf`.
- [Surprise — cấu hình học bias bằng ALS/SGD](https://surprise.readthedocs.io/en/stable/prediction_algorithms.html)
- [Surprise — các biến thể KNN](https://surprise.readthedocs.io/en/stable/knn_inspired.html)
- [Surprise — similarity và shrinkage](https://surprise.readthedocs.io/en/stable/similarities.html)
- [GroupLens — MovieLens 100K](https://grouplens.org/datasets/movielens/100k/)

**Generative AI:** tài liệu đặc tả này được soạn với sự hỗ trợ của ChatGPT. Khi nộp, nhóm cần cập nhật phạm vi sử dụng AI thực tế và cách kiểm chứng mã nguồn/kết quả; không coi bản thiết kế là bằng chứng đã triển khai.
