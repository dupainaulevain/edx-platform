(function(WAIT_TIMEOUT) {
    'use strict';
    describe('VideoAutoAdvance', function() {
        var state, oldOTBD;

        beforeEach(function() {
            oldOTBD = window.onTouchBasedDevice;
            window.onTouchBasedDevice = jasmine
                .createSpy('onTouchBasedDevice').and.returnValue(null);
            state = jasmine.initializePlayer('video.html');
            this.autoAdvanceEventStub = sinon.stub($('.sequence-nav-button.button-next').first(), 'clickEvent');
            $('.poster .btn-play').click();
            jasmine.clock().install();
        });

        afterEach(function() {
            $('source').remove();
            state.storage.clear();
            this.autoAdvanceEventStub.restore();
            if (state.videoPlayer) {
                state.videoPlayer.destroy();
            }
            window.onTouchBasedDevice = oldOTBD;
            jasmine.clock().uninstall();
        });

        describe('when video ends', function() {
            it('can autoadvance', function() {
                state.el.trigger('ended');
                jasmine.clock().tick(2);
                // FIXME Error: <toHaveBeenCalled> : Expected a spy, but got Function.
                expect(this.autoAdvanceEventStub).toHaveBeenCalled();
                expect(this.autoAdvanceEventStub.called).toBe(true);
            });
        });

    });
}).call(this, window.WAIT_TIMEOUT);
