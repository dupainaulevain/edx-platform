/* globals DiscussionUtil, DiscussionApp, DiscussionProfileApp */
var $$course_id = "{{course_id}}";

function DiscussionCourseBlock(runtime, element) {
    var testUrl = runtime.handlerUrl(element, 'test');
    if (testUrl.match(/^(http|https):\/\//)) {
        var hostname = testUrl.match(/^(.*:\/\/[a-z0-9:\-.]+)\//)[1];
        DiscussionUtil.setBaseUrl(hostname);
    }

    DiscussionUtil.force_async = true;

    $(function() {
        $("section.discussion").each(function(index, elem) {
           DiscussionApp.start(elem);
        });
        $("section.discussion-user-threads").each(function(index, elem) {
            DiscussionProfileApp.start(elem);
        });
    });
}
