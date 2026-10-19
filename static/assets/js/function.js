console.log("working fine");

const monthNames = ["Jan", "Feb", "Mar", "April", "May", "June",
    "July", "Aug", "Sept", "Oct", "Nov", "Dec"
];

$("#commentForm").submit(function (e) {
    e.preventDefault();

    let dt = new Date();
    let time = dt.getDay() + " " + monthNames[dt.getUTCMonth()] + ", " + dt.getFullYear()

    $.ajax({
        data: $(this).serialize(),

        method: $(this).attr("method"),

        url: $(this).attr("action"),

        dataType: "json",

        success: function (res) {
            console.log("Comment Saved to DB...");

            if (res.bool == true) {
                $("#review-res").text("نظر شما با موفقیت ثبت شد.")
                $(".hide-comment-form").hide()
                $(".add-review").hide()
                var rating = Number(res.context.rating) || 0;
                var stars = "";
                for (var i = 0; i < Math.min(Math.max(rating, 0), 5); i += 1) {
                    stars += "★";
                }
                $(".comment-list").prepend(
                    $("<article>", { class: "store-review" }).append(
                        $("<div>", { class: "store-review__meta" }).append(
                            $("<strong>").text(res.context.user),
                            $("<span>").text(time)
                        ),
                        $("<p>", { class: "store-review__rating" }).text(stars),
                        $("<p>").text(res.context.review)
                    )
                );
            }


        }
    })
})



$(document).ready(function () {
    function cartRequestHeaders() {
        const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
        return { "X-CSRFToken": csrfInput ? csrfInput.value : "" };
    }

    $(".filter-checkbox, #price-filter-btn").on("click", function () {
        console.log("A checkbox have been clicked");

        let filter_object = {}

        let min_price = $("#max_price").attr("min")
        let max_price = $("#max_price").val()

        filter_object.min_price = min_price;
        filter_object.max_price = max_price;

        $(".filter-checkbox").each(function () {
            let filter_value = $(this).val()
            let filter_key = $(this).data("filter") // vendor, category

            // console.log("Filter value is:", filter_value);
            // console.log("Filter key is:", filter_key);

            filter_object[filter_key] = Array.from(document.querySelectorAll('input[data-filter=' + filter_key + ']:checked')).map(function (element) {
                return element.value
            })
        })
        console.log("Filter Object is: ", filter_object);
        $.ajax({
            url: '/filter-products',
            data: filter_object,
            dataType: 'json',
            beforeSend: function () {
                console.log("Trying to filter product...");
            },
            success: function (response) {
                console.log(response.length);
                console.log("Data filtred successfully...");
                $(".totall-product").hide()
                $("#filtered-product").html(response.data)
            }
        })
    })

    $("#max_price").on("blur", function () {
        let min_price = $(this).attr("min")
        let max_price = $(this).attr("max")
        let current_price = $(this).val()

        // console.log("Current Price is:", current_price);
        // console.log("Max Price is:", max_price);
        // console.log("Min Price is:", min_price);

        if (current_price < parseInt(min_price) || current_price > parseInt(max_price)) {
            // console.log("Price Error Occured");

            min_price = Math.round(min_price * 100) / 100
            max_price = Math.round(max_price * 100) / 100


            // console.log("Max Price is:", min_Price);
            // console.log("Min Price is:", max_Price);

            alert("Price must between $" + min_price + ' and $' + max_price)
            $(this).val(min_price)
            $('#range').val(min_price)

            $(this).focus()

            return false

        }

    })

    // Add to cart functionality
    $(".add-to-cart-btn").on("click", function () {

        let this_val = $(this)
        let index = this_val.attr("data-index")

        let quantity = $(".product-quantity-" + index).val()
        let product_title = $(".product-title-" + index).val()

        let product_id = $(".product-id-" + index).val()
        let product_price = $(".current-product-price-" + index).text()

        let product_pid = $(".product-pid-" + index).val()
        let product_image = $(".product-image-" + index).val()


        console.log("Quantity:", quantity);
        console.log("Title:", product_title);
        console.log("Price:", product_price);
        console.log("ID:", product_id);
        console.log("PID:", product_pid);
        console.log("Image:", product_image);
        console.log("Index:", index);
        console.log("Currrent Element:", this_val);

        $.ajax({
            url: '/add-to-cart',
            method: 'POST',
            data: {
                'id': product_id,
                'pid': product_pid,
                'image': product_image,
                'qty': quantity,
                'title': product_title,
                'price': product_price,
            },
            headers: cartRequestHeaders(),
            dataType: 'json',
            beforeSend: function () {
                console.log("Adding Product to Cart...");
            },
            success: function (response) {
                // this_val.html("✓")
                this_val.html("<i class='fas fa-check-circle'></i>")

                console.log("Added Product to Cart!");
                $(".cart-items-count").text(response.totalcartitems)


            }
        })
    })


    $(".delete-product").on("click", function () {

        let product_id = $(this).attr("data-product")
        let this_val = $(this)

        console.log("PRoduct ID:", product_id);

        $.ajax({
            url: "/delete-from-cart",
            method: "POST",
            data: {
                "id": product_id
            },
            headers: cartRequestHeaders(),
            dataType: "json",
            beforeSend: function () {
                this_val.hide()
            },
            success: function (response) {
                this_val.show()
                $(".cart-items-count").text(response.totalcartitems)
                window.location.reload()
            }
        })

    })




    $(".update-product").on("click", function () {

        let product_id = $(this).attr("data-product")
        let this_val = $(this)
        let product_quantity = $(".product-qty-" + product_id).val()

        console.log("PRoduct ID:", product_id);
        console.log("PRoduct QTY:", product_quantity);

        $.ajax({
            url: "/update-cart",
            method: "POST",
            data: {
                "id": product_id,
                "qty": product_quantity,
            },
            headers: cartRequestHeaders(),
            dataType: "json",
            beforeSend: function () {
                this_val.hide()
            },
            success: function (response) {
                this_val.show()
                $(".cart-items-count").text(response.totalcartitems)
                window.location.reload()

            }
        })

    })


    $(document).on("submit", ".customer-dashboard__default-form", function (event) {
        event.preventDefault();
        const form = this;
        const button = form.querySelector("button[type='submit']");
        const token = form.querySelector("[name='csrfmiddlewaretoken']");
        if (!button || !token) return;

        button.disabled = true;
        fetch(form.action, {
            method: "POST",
            body: new FormData(form),
            credentials: "same-origin",
            headers: {
                "X-CSRFToken": token.value,
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json"
            }
        }).then(function (response) {
            return response.json().then(function (data) {
                if (!response.ok || data.boolean !== true) {
                    throw new Error(data.message || "تغییر نشانی پیش‌فرض انجام نشد.");
                }
                window.location.reload();
            });
        }).catch(function (error) {
            button.disabled = false;
            const message = form.querySelector(".account-form__error");
            if (message) {
                message.textContent = error.message;
            } else {
                const notice = document.createElement("span");
                notice.className = "account-form__error";
                notice.setAttribute("role", "alert");
                notice.textContent = error.message;
                form.appendChild(notice);
            }
        });
    });


    // Adding to wishlist
    $(document).on("click", ".add-to-wishlist", function () {
        let product_id = $(this).attr("data-product-item")
        let this_val = $(this)


        console.log("PRoduct ID IS", product_id);

        $.ajax({
            url: "/add-to-wishlist",
            data: {
                "id": product_id
            },
            dataType: "json",
            beforeSend: function () {
                console.log("Adding to wishlist...")
            },
            success: function (response) {
                // this_val.html("✓")
                this_val.html("<i class='fas fa-heart text-danger'></i>")
                if (response.bool === true) {
                    console.log("Added to wishlist...");
                }
            }
        })
    })


    // Remove from wishlist
    $(document).on("click", ".delete-wishlist-product", function () {
        let wishlist_id = $(this).attr("data-wishlist-product")
        let this_val = $(this)

        console.log("wishlist id is:", wishlist_id);

        $.ajax({
            url: "/remove-from-wishlist",
            data: {
                "id": wishlist_id
            },
            dataType: "json",
            beforeSend: function () {
                console.log("Deleting product from wishlist...");
            },
            success: function (response) {
                $("#wishlist-list").html(response.data)
            }
        })
    })


    $(document).on("submit", "#contact-form-ajax", function (e) {
        e.preventDefault()
        console.log("Submited...");

        let full_name = $("#full_name").val()
        let email = $("#email").val()
        let phone = $("#phone").val()
        let subject = $("#subject").val()
        let message = $("#message").val()

        console.log("Name:", full_name);
        console.log("Email:", email);
        console.log("Phone:", phone);
        console.log("Subject:", subject);
        console.log("MEssage:", message);

        $.ajax({
            url: "/ajax-contact-form",
            data: {
                "full_name": full_name,
                "email": email,
                "phone": phone,
                "subject": subject,
                "message": message,
            },
            dataType: "json",
            beforeSend: function () {
                console.log("Sending Data to Server...");
            },
            success: function (res) {
                console.log("Sent Data to server!");
                $(".contact_us_p").hide()
                $("#contact-form-ajax").hide()
                $("#message-response").html("Message sent successfully.")
            }
        })
    })




})







// // Add to cart functionality
// $(".add-to-cart-btn").on("click", function(){
//     let quantity = $("#product-quantity").val()
//     let product_title = $(".product-title").val()
//     let product_id = $(".product-id").val()
//     let product_price = $("#current-product-price").text()
//     let this_val = $(this)


//     console.log("Quantity:", quantity);
//     console.log("Title:", product_title);
//     console.log("Price:", product_price);
//     console.log("ID:", product_id);
//     console.log("Currrent Element:", this_val);

//     $.ajax({
//         url: '/add-to-cart',
//         data: {
//             'id': product_id,
//             'qty': quantity,
//             'title': product_title,
//             'price': product_price,
//         },
//         dataType: 'json',
//         beforeSend: function(){
//             console.log("Adding Product to Cart...");
//         },
//         success: function(response){
//             this_val.html("Item added to cart")
//             console.log("Added Product to Cart!");
//             $(".cart-items-count").text(response.totalcartitems)


//         }
//     })
// })